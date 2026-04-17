"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Plus, Sparkles, CheckCircle2, AlertTriangle, Check, X, Package, ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingOverlay } from "@/components/ui/LoadingOverlay";
import { useStudyStore } from "@/store/studyStore";
import { getStepVersions } from "@/lib/studyApi";
import type { StudyResponse, ConceptResponse, StepVersionResponse } from "@/types/study";

const TONE_OPTIONS = [
  "Aspirational", "Humorous", "Emotional/Heartfelt", "Bold/Disruptive",
  "Authoritative", "Warm/Reassuring", "Edgy", "Nostalgic", "Energetic",
];

const EMOTION_OPTIONS = [
  "Pride", "Warmth", "Curiosity", "Inspiration", "Reassurance",
  "Excitement", "Nostalgia", "Amusement", "Empowerment", "Belonging",
];

interface CreativeTerritoriesViewProps {
  study: StudyResponse;
  stepVersion: StepVersionResponse | null;
}

function TerritoryField({
  label,
  field,
  components,
  onChange,
  onAcceptSuggestion,
  onRejectSuggestion,
  multiline = false,
  placeholder = "",
}: {
  label: string;
  field: string;
  components: Record<string, any>;
  onChange: (field: string, value: string) => void;
  onAcceptSuggestion: (field: string) => void;
  onRejectSuggestion: (field: string) => void;
  multiline?: boolean;
  placeholder?: string;
}) {
  const data = components[field] || {};
  const raw = data.raw_input || "";
  const refined = data.refined;
  const rationale = data.refinement_rationale;

  return (
    <Card>
      <div className="space-y-2">
        <label className="text-xs font-medium uppercase tracking-wider text-white/40">{label}</label>
        {multiline ? (
          <textarea
            value={raw}
            onChange={(e) => onChange(field, e.target.value)}
            placeholder={placeholder}
            className="w-full h-24 px-3 py-2 bg-darpan-bg border border-darpan-border rounded-lg text-sm text-white placeholder-white/20 resize-none focus:outline-none focus:border-darpan-lime/40 transition-colors"
          />
        ) : (
          <input
            value={raw}
            onChange={(e) => onChange(field, e.target.value)}
            placeholder={placeholder}
            className="w-full px-3 py-2 bg-darpan-bg border border-darpan-border rounded-lg text-sm text-white placeholder-white/20 focus:outline-none focus:border-darpan-lime/40 transition-colors"
          />
        )}
        {refined && refined !== raw && (
          <div className="mt-1 px-3 py-2 rounded-lg bg-darpan-lime/5 border border-darpan-lime/10">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-xs text-darpan-lime/70 font-medium mb-1">AI Suggestion:</p>
                <p className="text-xs text-white/60 leading-relaxed">{refined}</p>
                {rationale && (
                  <p className="text-[10px] text-white/25 mt-1 italic">{rationale}</p>
                )}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => onAcceptSuggestion(field)}
                  title="Accept — replace with AI version"
                  className="p-1 rounded hover:bg-darpan-lime/10 text-darpan-lime transition-colors"
                >
                  <Check className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => onRejectSuggestion(field)}
                  title="Reject — keep original"
                  className="p-1 rounded hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

function ProductBriefSummary({ studyId }: { studyId: string }) {
  const [pb, setPb] = useState<Record<string, unknown> | null>(null);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    getStepVersions(studyId, 2)
      .then((versions) => {
        const locked = versions.filter((v) => v.status === "locked").slice(-1)[0];
        if (locked) setPb(locked.content);
      })
      .catch(() => {});
  }, [studyId]);

  if (!pb) return null;

  const name = (pb.product_name as string) || "—";
  const category = (pb.category as string) || "—";
  const keyMsg = (pb.must_communicate as string) || "";
  const traits = (pb.brand_personality_traits as string[]) || [];

  return (
    <Card className="border-darpan-lime/15 bg-darpan-lime/[0.03]">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2.5">
          <Package className="w-4 h-4 text-darpan-lime/80" />
          <span className="text-xs font-medium uppercase tracking-wider text-darpan-lime/80">
            Product Brief
          </span>
          <span className="text-sm text-white/70">— {name}</span>
          <span className="text-xs text-white/40">({category})</span>
        </div>
        {expanded ? (
          <ChevronUp className="w-3.5 h-3.5 text-white/40" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-white/40" />
        )}
      </button>
      {expanded && (
        <div className="mt-3 space-y-2 text-sm text-white/60">
          {keyMsg && (
            <div>
              <span className="text-[10px] uppercase tracking-wider text-white/30">Must communicate: </span>
              <span className="text-white/80">{keyMsg}</span>
            </div>
          )}
          {traits.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] uppercase tracking-wider text-white/30 mr-1">Personality:</span>
              {traits.map((t) => (
                <span
                  key={t}
                  className="px-2 py-0.5 rounded text-xs bg-darpan-bg border border-darpan-border text-white/60"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}


export function CreativeTerritoriesView({ study, stepVersion }: CreativeTerritoriesViewProps) {
  const {
    concepts,
    addConcept,
    deleteConcept,
    updateConcept,
    refineConcept,
    approveConcept,
    loading,
    loadingMessage,
  } = useStudyStore();

  const [activeTab, setActiveTab] = useState(0);

  // Territories are at step 3 for ad_creative. They're "locked" only once
  // step 3 itself is locked (status step_3_locked) or study has moved past it.
  const isLocked =
    study.status === "step_3_locked" ||
    study.status.startsWith("step_4") ||
    study.status.startsWith("step_5") ||
    study.status === "complete";

  if (concepts.length === 0 && !stepVersion) {
    return (
      <div className="text-center py-16">
        <div className="w-14 h-14 rounded-2xl bg-darpan-surface border border-darpan-border flex items-center justify-center mx-auto mb-4">
          <Sparkles className="w-7 h-7 text-white/20" />
        </div>
        <p className="text-white/30 text-sm">
          Click Generate to create creative territory templates
        </p>
      </div>
    );
  }

  const sortedConcepts = [...concepts].sort((a, b) => a.concept_index - b.concept_index);
  const currentTerritory = sortedConcepts[activeTab];

  const handleFieldChange = async (field: string, value: string) => {
    if (!currentTerritory) return;
    const components = { ...(currentTerritory.components as Record<string, any>) };
    if (typeof components[field] === "object" && components[field] !== null) {
      components[field] = { ...components[field], raw_input: value };
    } else {
      components[field] = { raw_input: value, refined: null, approved: false };
    }
    await updateConcept(currentTerritory.id, components);
  };

  const handleAcceptSuggestion = async (field: string) => {
    if (!currentTerritory) return;
    const components = { ...(currentTerritory.components as Record<string, any>) };
    const existing = components[field];
    if (existing && typeof existing === "object" && existing.refined) {
      components[field] = {
        ...existing,
        raw_input: existing.refined,
        refined: null,
        refinement_rationale: null,
        approved: true,
      };
      await updateConcept(currentTerritory.id, components);
      toast.success("AI suggestion accepted");
    }
  };

  const handleRejectSuggestion = async (field: string) => {
    if (!currentTerritory) return;
    const components = { ...(currentTerritory.components as Record<string, any>) };
    const existing = components[field];
    if (existing && typeof existing === "object") {
      components[field] = {
        ...existing,
        refined: null,
        refinement_rationale: null,
      };
      await updateConcept(currentTerritory.id, components);
    }
  };

  const handleToneToggle = async (tone: string) => {
    if (!currentTerritory) return;
    const raw = (currentTerritory.components as Record<string, any>).tone_mood;
    // Backward compat: if tone_mood was a single string, convert to array
    const current: string[] = Array.isArray(raw) ? raw : raw ? [raw as string] : [];
    const next = current.includes(tone)
      ? current.filter((t) => t !== tone)
      : current.length < 3
        ? [...current, tone]
        : current;
    const components = { ...(currentTerritory.components as Record<string, any>), tone_mood: next };
    await updateConcept(currentTerritory.id, components);
  };

  const handleEmotionToggle = async (emotion: string) => {
    if (!currentTerritory) return;
    const current = (currentTerritory.components as Record<string, any>).target_emotion || [];
    const next = current.includes(emotion)
      ? current.filter((e: string) => e !== emotion)
      : current.length < 3
        ? [...current, emotion]
        : current;
    const components = { ...(currentTerritory.components as Record<string, any>), target_emotion: next };
    await updateConcept(currentTerritory.id, components);
  };

  const handleRefine = async () => {
    if (!currentTerritory) return;
    try {
      await refineConcept(currentTerritory.id);
      toast.success("Territory refined");
    } catch {
      // Error set in store
    }
  };

  const handleApprove = async () => {
    if (!currentTerritory) return;
    try {
      await approveConcept(currentTerritory.id, {
        territory_name: true,
        core_insight: true,
        big_idea: true,
        key_message: true,
        execution_sketch: true,
      });
      toast.success("Territory approved");
    } catch (e) {
      toast.error("Could not approve: " + (e as Error).message);
    }
  };

  const handleDelete = async () => {
    if (!currentTerritory) return;
    if (!confirm(`Delete Territory ${currentTerritory.concept_index}? This cannot be undone.`)) return;
    try {
      await deleteConcept(currentTerritory.id);
      // Move focus to prior tab
      setActiveTab((prev) => Math.max(0, prev - 1));
      toast.success("Territory deleted");
    } catch (e) {
      toast.error("Could not delete: " + (e as Error).message);
    }
  };

  const components = (currentTerritory?.components || {}) as Record<string, any>;
  const territoryName =
    components.territory_name?.raw_input ||
    components.territory_name?.refined ||
    `Territory ${currentTerritory?.concept_index || activeTab + 1}`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-5"
    >
      {/* Product Brief summary — locked step 2 content */}
      <ProductBriefSummary studyId={study.id} />

      {/* Tabs */}
      <div className="flex items-center gap-2 flex-wrap">
        {sortedConcepts.map((t, i) => (
          <button
            key={t.id || i}
            onClick={() => setActiveTab(i)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              i === activeTab
                ? "bg-darpan-surface border border-darpan-lime/30 text-white"
                : "text-white/50 hover:text-white hover:bg-white/5"
            }`}
          >
            Territory {i + 1}
            {t.status === "approved" && (
              <CheckCircle2 className="w-3 h-3 ml-1.5 inline text-darpan-lime" />
            )}
          </button>
        ))}

        {!isLocked && (
          <div className="flex items-center gap-2 ml-auto">
            <button
              onClick={async () => {
                await addConcept();
                setActiveTab(concepts.length);
                toast.success("Territory added");
              }}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white/50 hover:text-white bg-white/5 rounded-lg transition-colors disabled:opacity-50"
            >
              <Plus className="w-3 h-3" />
              Add Territory
            </button>
          </div>
        )}
      </div>

      {/* Active territory detail */}
      {currentTerritory && (
        <div className="space-y-3 relative">
          <LoadingOverlay visible={loading} message={loadingMessage} />

          {/* Header with status + actions */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <h3 className="text-base font-semibold text-white">{territoryName}</h3>
              <Badge
                variant={
                  currentTerritory.status === "approved"
                    ? "lime"
                    : currentTerritory.status === "refined"
                      ? "cyan"
                      : "default"
                }
              >
                {currentTerritory.status}
              </Badge>
            </div>
            {!isLocked && (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleRefine}
                  disabled={loading}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-darpan-cyan/10 border border-darpan-cyan/20 text-darpan-cyan text-xs font-medium rounded-lg hover:bg-darpan-cyan/15 transition-colors disabled:opacity-50"
                >
                  <Sparkles className="w-3 h-3" />
                  Refine with AI
                </button>
                {currentTerritory.status === "refined" && (
                  <button
                    onClick={handleApprove}
                    disabled={loading}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-darpan-lime/10 border border-darpan-lime/20 text-darpan-lime text-xs font-medium rounded-lg hover:bg-darpan-lime/15 transition-colors disabled:opacity-50"
                  >
                    <Check className="w-3 h-3" />
                    Approve
                  </button>
                )}
                {sortedConcepts.length > 1 && (
                  <button
                    onClick={handleDelete}
                    disabled={loading}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium rounded-lg hover:bg-red-500/15 transition-colors disabled:opacity-50"
                    title="Delete this territory"
                  >
                    <Trash2 className="w-3 h-3" />
                    Delete
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Flags */}
          {currentTerritory.comparability_flags &&
            (currentTerritory.comparability_flags as string[]).length > 0 && (
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/5 border border-amber-500/10">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                <p className="text-xs text-amber-400/70">
                  {(currentTerritory.comparability_flags as string[]).join(", ")}
                </p>
              </div>
            )}

          {/* Fields */}
          <TerritoryField
            label="Territory Name"
            field="territory_name"
            components={components}
            onChange={handleFieldChange}
            onAcceptSuggestion={handleAcceptSuggestion}
            onRejectSuggestion={handleRejectSuggestion}
            placeholder="e.g., The Everyday Hero"
          />
          <TerritoryField
            label="Core Insight (25-150 words, consumer voice)"
            field="core_insight"
            components={components}
            onChange={handleFieldChange}
            onAcceptSuggestion={handleAcceptSuggestion}
            onRejectSuggestion={handleRejectSuggestion}
            multiline
            placeholder="The human truth this territory is rooted in..."
          />
          <TerritoryField
            label="Big Idea (25-150 words)"
            field="big_idea"
            components={components}
            onChange={handleFieldChange}
            onAcceptSuggestion={handleAcceptSuggestion}
            onRejectSuggestion={handleRejectSuggestion}
            multiline
            placeholder="The creative concept in plain language..."
          />
          <TerritoryField
            label="Key Message / Tagline"
            field="key_message"
            components={components}
            onChange={handleFieldChange}
            onAcceptSuggestion={handleAcceptSuggestion}
            onRejectSuggestion={handleRejectSuggestion}
            placeholder="e.g., Finish earlier. Live more."
          />

          {/* Tone & Mood — dedicated card (multi-select, up to 3) */}
          <Card>
            <div className="space-y-2">
              <label className="text-xs font-medium uppercase tracking-wider text-white/40">
                Tone & Mood (1-3)
              </label>
              <div className="flex flex-wrap gap-1.5">
                {TONE_OPTIONS.map((tone) => {
                  const raw = components.tone_mood;
                  const selectedList: string[] = Array.isArray(raw) ? raw : raw ? [raw as string] : [];
                  const selected = selectedList.includes(tone);
                  return (
                    <button
                      key={tone}
                      onClick={() => handleToneToggle(tone)}
                      disabled={isLocked}
                      className={`px-2.5 py-1 rounded-md text-xs transition-colors ${
                        selected
                          ? "bg-darpan-lime/15 text-darpan-lime border border-darpan-lime/30"
                          : "bg-darpan-bg border border-darpan-border text-white/40 hover:text-white/60"
                      }`}
                    >
                      {tone}
                    </button>
                  );
                })}
              </div>
            </div>
          </Card>

          <TerritoryField
            label="Execution Sketch (3-5 sentences)"
            field="execution_sketch"
            components={components}
            onChange={handleFieldChange}
            onAcceptSuggestion={handleAcceptSuggestion}
            onRejectSuggestion={handleRejectSuggestion}
            multiline
            placeholder="What a finished ad might look like: setting, characters, story arc..."
          />

          {/* Target Emotion — dedicated card */}
          <Card>
            <div className="space-y-2">
              <label className="text-xs font-medium uppercase tracking-wider text-white/40">
                Target Emotion (1-3)
              </label>
              <div className="flex flex-wrap gap-1.5">
                {EMOTION_OPTIONS.map((emotion) => {
                  const selected = (components.target_emotion || []).includes(emotion);
                  return (
                    <button
                      key={emotion}
                      onClick={() => handleEmotionToggle(emotion)}
                      disabled={isLocked}
                      className={`px-2.5 py-1 rounded-md text-xs transition-colors ${
                        selected
                          ? "bg-darpan-cyan/15 text-darpan-cyan border border-darpan-cyan/30"
                          : "bg-darpan-bg border border-darpan-border text-white/40 hover:text-white/60"
                      }`}
                    >
                      {emotion}
                    </button>
                  );
                })}
              </div>
            </div>
          </Card>
        </div>
      )}
    </motion.div>
  );
}
