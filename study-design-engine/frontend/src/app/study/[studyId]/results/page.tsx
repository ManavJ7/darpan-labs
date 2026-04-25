"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Loader2, BarChart3 } from "lucide-react";
import { toast } from "sonner";
import { Sidebar } from "@/components/layout/Sidebar";
import { ResultsFilters } from "@/components/results/ResultsFilters";
import { ScoreTable } from "@/components/results/ScoreTable";
import { Recommendation } from "@/components/results/Recommendation";
import { QualitativeSummary } from "@/components/results/QualitativeSummary";
import { TerritoryScorecard } from "@/components/results/TerritoryScorecard";
import { CompareDecide } from "@/components/results/CompareDecide";
import { useAuthStore } from "@/store/authStore";
import {
  getStudy,
  getStepVersions,
  getConcepts,
  listTwinSimulationResults,
  type TwinSimulationResult,
} from "@/lib/studyApi";
import {
  processResults,
  generateRecommendation,
  getConceptName,
  buildQuestionMapping,
  guessNumToSelect,
} from "@/lib/resultsEngine";
import { processAdCreativeResults, type AdCreativeResults } from "@/lib/adCreativeResultsEngine";
import type {
  StudyResponse,
  ConceptResponse,
  QuestionnaireSection,
  StepVersionResponse,
} from "@/types/study";

export default function ResultsDashboardPage() {
  const params = useParams();
  const studyId = params.studyId as string;
  const { user } = useAuthStore();

  // Raw data
  const [study, setStudy] = useState<StudyResponse | null>(null);
  const [briefContent, setBriefContent] = useState<Record<string, unknown> | null>(null);
  const [productBrief, setProductBrief] = useState<Record<string, unknown> | null>(null);
  const [concepts, setConcepts] = useState<ConceptResponse[]>([]);
  const [sections, setSections] = useState<QuestionnaireSection[]>([]);
  const [simResults, setSimResults] = useState<TwinSimulationResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state (pending — applied on "Apply")
  const [pendingTwins, setPendingTwins] = useState<Set<string>>(new Set());
  const [pendingConcepts, setPendingConcepts] = useState<Set<number>>(new Set());
  const [pendingMetrics, setPendingMetrics] = useState<Set<string>>(new Set());

  // Applied filter state
  const [appliedTwins, setAppliedTwins] = useState<Set<string>>(new Set());
  const [appliedConcepts, setAppliedConcepts] = useState<Set<number>>(new Set());
  const [appliedMetrics, setAppliedMetrics] = useState<Set<string>>(new Set());

  // Concepts to select — set by user in the wizard, stored in localStorage
  const [numToSelect, setNumToSelect] = useState<number>(1);

  // ─── Data fetching ───────────────────────────────────
  useEffect(() => {
    async function load() {
      try {
        setLoading(true);

        const [studyData, conceptsData, simData] = await Promise.all([
          getStudy(studyId),
          getConcepts(studyId).catch(() => []),
          listTwinSimulationResults(studyId).catch(() => []),
        ]);

        setStudy(studyData);
        setConcepts(conceptsData);
        setSimResults(simData);

        // Fetch step 1 (brief) for recommended_metrics
        const step1Versions = await getStepVersions(studyId, 1).catch(() => []);
        if (step1Versions.length > 0) {
          setBriefContent(step1Versions[step1Versions.length - 1].content);
        }

        // Determine study type
        const sType = (studyData.study_metadata as Record<string, unknown>)?.study_type as string | undefined;
        const isAd = sType === "ad_creative_testing";

        // For ad_creative_testing: fetch step 2 (Product Brief)
        if (isAd) {
          const step2Versions = await getStepVersions(studyId, 2).catch(() => []);
          if (step2Versions.length > 0) {
            setProductBrief(step2Versions[step2Versions.length - 1].content);
          }
        }

        // Fetch questionnaire: step 4 for concept_testing, step 5 for ad_creative_testing
        const qStep = isAd ? 5 : 4;
        const qVersions = await getStepVersions(studyId, qStep).catch(() => []);
        if (qVersions.length > 0) {
          const q = qVersions[qVersions.length - 1].content;
          if (q?.sections) {
            setSections(q.sections as unknown as QuestionnaireSection[]);
          }
        }

        // Initialize filters: select all by default
        const completedTwins = simData
          .filter((r: TwinSimulationResult) => r.status === "completed")
          .map((r: TwinSimulationResult) => r.twin_id);
        const allTwins = new Set(completedTwins);
        const allConceptIndices = new Set(conceptsData.map((c: ConceptResponse) => c.concept_index));

        setPendingTwins(new Set(allTwins));
        setPendingConcepts(new Set(allConceptIndices));
        setAppliedTwins(new Set(allTwins));
        setAppliedConcepts(new Set(allConceptIndices));

        // Read concepts-to-select from localStorage (set by user in wizard)
        // Fall back to best-guess from question text if not set
        const stored = localStorage.getItem(`concepts_to_select_${studyId}`);
        if (stored) {
          setNumToSelect(parseInt(stored, 10) || 1);
        } else {
          setNumToSelect(guessNumToSelect(studyData.question));
        }

        // Metrics: will be set after initial processing
        // We need to process once to discover available metrics
        setLoading(false);
      } catch (e) {
        setError((e as Error).message);
        setLoading(false);
      }
    }
    load();
  }, [studyId]);

  // Discover available metrics using the same mapping logic as processResults
  const discoveredMetrics = useMemo(() => {
    if (sections.length === 0 || concepts.length === 0) return [];
    const mapping = buildQuestionMapping(sections, concepts);
    const allMetricIds = new Set<string>();
    for (const [, m] of mapping) {
      if (m.metricId && m.isScorable) allMetricIds.add(m.metricId);
    }
    return Array.from(allMetricIds);
  }, [sections, concepts]);

  // Set metric filters once discovered
  useEffect(() => {
    if (discoveredMetrics.length > 0 && pendingMetrics.size === 0) {
      const s = new Set(discoveredMetrics);
      setPendingMetrics(s);
      setAppliedMetrics(new Set(s));
    }
  }, [discoveredMetrics, pendingMetrics.size]);

  // ─── Process results ─────────────────────────────────
  const processed = useMemo(() => {
    if (
      simResults.length === 0 ||
      sections.length === 0 ||
      concepts.length === 0 ||
      appliedMetrics.size === 0
    ) {
      return null;
    }
    return processResults(
      simResults,
      sections,
      concepts,
      appliedTwins,
      appliedConcepts,
      appliedMetrics,
    );
  }, [simResults, sections, concepts, appliedTwins, appliedConcepts, appliedMetrics]);

  // ─── Study type ───────────────────────────────────────
  const studyType = (study?.study_metadata as Record<string, unknown>)?.study_type as string | undefined;
  const isAdCreative = studyType === "ad_creative_testing";

  // ─── Ad Creative results ────────────────────────────
  const adCreativeResults = useMemo<AdCreativeResults | null>(() => {
    if (!isAdCreative || simResults.length === 0 || sections.length === 0 || concepts.length === 0) return null;
    const campaignObj = (briefContent as Record<string, unknown>)?.campaign_objective as string || "default";
    return processAdCreativeResults(simResults, sections, concepts, campaignObj);
  }, [isAdCreative, simResults, sections, concepts, briefContent]);

  // ─── Recommendation ──────────────────────────────────
  const recommendation = useMemo(() => {
    if (!processed) return null;
    return {
      ...generateRecommendation(processed.scoreRows, numToSelect),
      numToSelect,
    };
  }, [processed, numToSelect]);

  // ─── Filter helpers ──────────────────────────────────
  const toggleSet = <T,>(set: Set<T>, val: T): Set<T> => {
    const next = new Set(set);
    if (next.has(val)) next.delete(val);
    else next.add(val);
    return next;
  };

  const twinItems = useMemo(
    () =>
      simResults
        .filter((r) => r.status === "completed")
        .map((r) => ({ id: r.twin_id, label: r.twin_external_id })),
    [simResults],
  );

  const conceptItems = useMemo(
    () =>
      concepts
        .sort((a, b) => a.concept_index - b.concept_index)
        .map((c) => ({
          id: String(c.concept_index),
          label: getConceptName(c),
        })),
    [concepts],
  );

  const metricItems = useMemo(() => {
    if (!processed) {
      return discoveredMetrics.map((id) => ({
        id,
        label: id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      }));
    }
    return processed.availableMetrics;
  }, [processed, discoveredMetrics]);

  // Convert concept filters between number set and string set for the filter component
  const pendingConceptStrings = useMemo(
    () => new Set(Array.from(pendingConcepts).map(String)),
    [pendingConcepts],
  );

  const handleApply = useCallback(() => {
    setAppliedTwins(new Set(pendingTwins));
    setAppliedConcepts(new Set(pendingConcepts));
    setAppliedMetrics(new Set(pendingMetrics));
    toast.success("Filters applied");
  }, [pendingTwins, pendingConcepts, pendingMetrics]);

  const handleReset = useCallback(() => {
    const allTwins = new Set(twinItems.map((t) => t.id));
    const allConcepts = new Set(concepts.map((c) => c.concept_index));
    const allMetrics = new Set(discoveredMetrics);
    setPendingTwins(allTwins);
    setPendingConcepts(allConcepts);
    setPendingMetrics(allMetrics);
    setAppliedTwins(new Set(allTwins));
    setAppliedConcepts(new Set(allConcepts));
    setAppliedMetrics(new Set(allMetrics));
    toast.success("Filters reset");
  }, [twinItems, concepts, discoveredMetrics]);

  // ─── Avatar helper ───────────────────────────────────
  const getInitials = () => {
    const str = user?.name || user?.email || "U";
    return str
      .split(" ")
      .map((w) => w[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  // ─── Render ──────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-white/30 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-sm text-red-400">{error}</p>
      </div>
    );
  }

  const completedCount = simResults.filter((r) => r.status === "completed").length;
  const hasResults = completedCount > 0 && sections.length > 0 && concepts.length > 0;

  const validationUrl = process.env.NEXT_PUBLIC_VALIDATION_URL;
  const showValidationButton =
    hasResults &&
    !!validationUrl &&
    study?.brand_name?.toLowerCase() === "dove";

  return (
    <div className="min-h-screen flex">
      <Sidebar activePage="Studies" />

      <div className="flex-1 ml-0 md:ml-[60px] flex flex-col">
        {/* Top bar */}
        <div className="flex items-center justify-between gap-2 px-4 sm:px-6 h-12 shrink-0">
          <div className="flex items-center gap-2 text-sm">
            <Link
              href="/"
              className="text-white/40 hover:text-white/60 transition-colors"
            >
              Studies
            </Link>
            <span className="text-white/20">/</span>
            <Link
              href={`/study/${studyId}`}
              className="text-white/40 hover:text-white/60 transition-colors max-w-[200px] truncate"
            >
              {study?.title || "Study"}
            </Link>
            <span className="text-white/20">/</span>
            <span className="text-white/60 font-medium">Results</span>
          </div>
          {user && (
            <div>
              {user.picture_url ? (
                <img
                  src={user.picture_url}
                  alt=""
                  className="w-8 h-8 rounded-full"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <div className="w-8 h-8 rounded-full bg-darpan-elevated border border-darpan-border flex items-center justify-center text-[10px] font-semibold text-white/70">
                  {getInitials()}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Content */}
        <main className="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 py-6 sm:py-8">
          {/* Header */}
          <div className="flex items-center gap-4 mb-8">
            <Link
              href={`/study/${studyId}`}
              className="w-8 h-8 rounded-lg bg-darpan-surface border border-darpan-border flex items-center justify-center text-white/40 hover:text-white/70 hover:border-darpan-border-active transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold">Results Dashboard</h1>
              <p className="text-sm text-white/35 mt-0.5">
                {completedCount} twin simulation{completedCount !== 1 ? "s" : ""} &middot;{" "}
                {concepts.length} concept{concepts.length !== 1 ? "s" : ""}
              </p>
            </div>
            {showValidationButton && (
              <a
                href={validationUrl!}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 rounded-md bg-cyan-600 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-500 transition-colors shrink-0"
              >
                <BarChart3 className="w-4 h-4" />
                View Validation Dashboard
              </a>
            )}
          </div>

          {!hasResults ? (
            <div className="bg-darpan-surface border border-darpan-border rounded-xl p-12 text-center">
              <p className="text-white/40 text-sm mb-3">
                No simulation results available yet.
              </p>
              <Link
                href={`/study/${studyId}`}
                className="text-sm text-darpan-lime hover:text-darpan-lime-dim transition-colors"
              >
                Go back to run twin simulations
              </Link>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Research Question */}
              {study?.question && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-darpan-surface border border-darpan-border rounded-xl px-5 py-4"
                >
                  <p className="text-xs font-medium text-white/30 uppercase tracking-wider mb-1.5">
                    Research Question
                  </p>
                  <p className="text-sm text-white/60 leading-relaxed">
                    {study.question}
                  </p>
                </motion.div>
              )}

              {/* Filters */}
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 }}
              >
                <ResultsFilters
                  twinFilter={{
                    label: "Twins",
                    items: twinItems,
                    selected: pendingTwins,
                    onToggle: (id) => setPendingTwins(toggleSet(pendingTwins, id)),
                    onToggleAll: () =>
                      setPendingTwins(
                        pendingTwins.size === twinItems.length
                          ? new Set()
                          : new Set(twinItems.map((t) => t.id)),
                      ),
                  }}
                  conceptFilter={{
                    label: "Concepts",
                    items: conceptItems,
                    selected: pendingConceptStrings,
                    onToggle: (id) =>
                      setPendingConcepts(toggleSet(pendingConcepts, parseInt(id, 10))),
                    onToggleAll: () =>
                      setPendingConcepts(
                        pendingConcepts.size === conceptItems.length
                          ? new Set()
                          : new Set(concepts.map((c) => c.concept_index)),
                      ),
                  }}
                  metricFilter={{
                    label: "Metrics",
                    items: metricItems,
                    selected: pendingMetrics,
                    onToggle: (id) => setPendingMetrics(toggleSet(pendingMetrics, id)),
                    onToggleAll: () =>
                      setPendingMetrics(
                        pendingMetrics.size === metricItems.length
                          ? new Set()
                          : new Set(metricItems.map((m) => m.id)),
                      ),
                  }}
                  onApply={handleApply}
                  onReset={handleReset}
                />
              </motion.div>

              {/* ─── Ad Creative Results ─── */}
              {isAdCreative && adCreativeResults && (
                <>
                  {/* Tab 1: Territory Scorecards */}
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                  >
                    <TerritoryScorecard
                      territories={adCreativeResults.territories}
                      productBrief={productBrief}
                    />
                  </motion.div>

                  {/* Tab 2: Compare & Decide */}
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15 }}
                  >
                    <CompareDecide
                      territories={adCreativeResults.territories}
                      availableMetrics={adCreativeResults.availableMetrics}
                      numToSelect={numToSelect}
                    />
                  </motion.div>
                </>
              )}

              {/* ─── Concept Testing Results ─── */}
              {!isAdCreative && (
                <>
                  {/* Score Table */}
                  {processed && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.1 }}
                    >
                      <ScoreTable
                        rows={processed.scoreRows}
                        metricIds={Array.from(appliedMetrics)}
                      />
                    </motion.div>
                  )}

                  {/* Recommendation */}
                  {recommendation && processed && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.15 }}
                    >
                      <Recommendation
                        recommended={recommendation.recommended}
                        explanation={recommendation.explanation}
                        numToSelect={recommendation.numToSelect}
                        allRows={processed.scoreRows}
                      />
                    </motion.div>
                  )}
                </>
              )}

              {/* Qualitative Summary — shared across both study types */}
              {processed && processed.qualitativeEntries.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                >
                  <QualitativeSummary entries={processed.qualitativeEntries} studyId={studyId} />
                </motion.div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
