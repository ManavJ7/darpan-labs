"use client";

import { useEffect, useState } from "react";
import {
  MessageSquare,
  ChevronDown,
  ChevronUp,
  Loader2,
  RefreshCw,
  ThumbsUp,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import {
  getQualitativeInsights,
  type ConceptInsight,
  type ThemeItem,
  type QualitativeInsightsResponse,
} from "@/lib/studyApi";
import type { QualitativeEntry } from "@/lib/resultsEngine";

// ─── Sentiment helpers ─────────────────────────────────

function sentimentColor(s: string) {
  switch (s) {
    case "positive":
      return { text: "text-green-400", bg: "bg-green-400/10", bar: "bg-green-400/30" };
    case "negative":
      return { text: "text-red-400", bg: "bg-red-400/10", bar: "bg-red-400/30" };
    case "mixed":
      return { text: "text-amber-400", bg: "bg-amber-400/10", bar: "bg-amber-400/30" };
    default:
      return { text: "text-white/40", bg: "bg-white/5", bar: "bg-white/10" };
  }
}

// ─── Theme bar ─────────────────────────────────────────

function ThemeBar({ theme, total }: { theme: ThemeItem; total: number }) {
  const pct = total > 0 ? (theme.frequency / total) * 100 : 0;
  const sc = sentimentColor(theme.sentiment);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm text-white/70 font-medium truncate">
            {theme.theme_name}
          </span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${sc.bg} ${sc.text}`}>
            {theme.sentiment}
          </span>
        </div>
        <span className="text-xs text-white/30 shrink-0 tabular-nums font-mono">
          {theme.frequency} of {total}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
        <div
          className={`h-full rounded-full ${sc.bar} transition-all duration-500`}
          style={{ width: `${Math.max(pct, 3)}%` }}
        />
      </div>
      <p className="text-xs text-white/25 italic pl-1 line-clamp-2">
        &ldquo;{theme.representative_quote}&rdquo;
      </p>
    </div>
  );
}

// ─── Concept insight card ──────────────────────────────

function ConceptInsightCard({
  appealing,
  improve,
}: {
  appealing?: ConceptInsight;
  improve?: ConceptInsight;
}) {
  const [tab, setTab] = useState<"appealing" | "improve">("appealing");
  const [expanded, setExpanded] = useState(true);

  const active = tab === "appealing" ? appealing : improve;
  const conceptName = appealing?.concept_name || improve?.concept_name || "Concept";

  if (!appealing && !improve) return null;

  return (
    <div className="border border-darpan-border rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-darpan-bg/50 hover:bg-white/[0.02] transition-colors"
      >
        <span className="text-sm font-medium text-white/70">{conceptName}</span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-white/25">
            {(appealing?.response_count || 0) + (improve?.response_count || 0)} responses
          </span>
          {expanded ? (
            <ChevronUp className="w-3.5 h-3.5 text-white/30" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5 text-white/30" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="p-4 space-y-4">
          {/* Tabs */}
          <div className="flex gap-1 p-0.5 rounded-lg bg-darpan-bg/80 w-fit">
            {appealing && (
              <button
                onClick={() => setTab("appealing")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  tab === "appealing"
                    ? "bg-green-500/15 text-green-400"
                    : "text-white/30 hover:text-white/50"
                }`}
              >
                <ThumbsUp className="w-3 h-3" />
                Appealing
              </button>
            )}
            {improve && (
              <button
                onClick={() => setTab("improve")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  tab === "improve"
                    ? "bg-amber-500/15 text-amber-400"
                    : "text-white/30 hover:text-white/50"
                }`}
              >
                <AlertTriangle className="w-3 h-3" />
                Needs Improvement
              </button>
            )}
          </div>

          {active && (
            <div className="space-y-4">
              {/* Summary */}
              <p className="text-sm text-white/50 leading-relaxed">
                {active.summary}
              </p>

              {/* Themes */}
              <div className="space-y-3">
                {active.themes.map((theme, i) => (
                  <ThemeBar
                    key={i}
                    theme={theme}
                    total={active.response_count}
                  />
                ))}
              </div>

              {/* Representative quotes */}
              {active.representative_quotes.length > 0 && (
                <div className="pt-2 border-t border-darpan-border/50">
                  <p className="text-[10px] text-white/20 uppercase tracking-wider mb-2">
                    Key quotes
                  </p>
                  {active.representative_quotes.map((q, i) => (
                    <p
                      key={i}
                      className="text-xs text-white/35 italic leading-relaxed mb-1.5"
                    >
                      &ldquo;{q}&rdquo;
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Fallback: raw entries (original behavior) ─────────

function RawEntries({ entries }: { entries: QualitativeEntry[] }) {
  const grouped = new Map<string, QualitativeEntry[]>();
  for (const entry of entries) {
    if (!grouped.has(entry.conceptName)) grouped.set(entry.conceptName, []);
    grouped.get(entry.conceptName)!.push(entry);
  }

  return (
    <div className="space-y-3">
      {Array.from(grouped.entries()).map(([name, items]) => (
        <div key={name} className="border border-darpan-border rounded-lg p-4">
          <p className="text-sm font-medium text-white/70 mb-2">{name}</p>
          {items.map((entry, i) => (
            <div key={i} className="mb-2">
              <p className="text-xs text-white/40 mb-1">{entry.questionText}</p>
              {entry.answers.slice(0, 5).map((a, j) => (
                <p key={j} className="text-xs text-white/30 pl-3">
                  &bull; {a}
                </p>
              ))}
              {entry.answers.length > 5 && (
                <p className="text-xs text-white/15 pl-3">
                  +{entry.answers.length - 5} more
                </p>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// ─── Main component ────────────────────────────────────

interface QualitativeSummaryProps {
  entries: QualitativeEntry[];
  studyId: string;
}

export function QualitativeSummary({ entries, studyId }: QualitativeSummaryProps) {
  const [data, setData] = useState<QualitativeInsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchInsights = (forceRefresh = false) => {
    setLoading(true);
    setError(false);
    getQualitativeInsights(studyId, forceRefresh)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((e) => {
        console.error("Failed to load qualitative insights:", e);
        setError(true);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchInsights();
  }, [studyId]);

  if (entries.length === 0 && !data?.insights?.length) return null;

  // Group insights by concept for paired (appealing + improve) cards
  const insightsByConceptPair = new Map<
    number,
    { appealing?: ConceptInsight; improve?: ConceptInsight }
  >();
  if (data?.insights) {
    for (const insight of data.insights) {
      if (!insightsByConceptPair.has(insight.concept_index)) {
        insightsByConceptPair.set(insight.concept_index, {});
      }
      const pair = insightsByConceptPair.get(insight.concept_index)!;
      if (insight.question_type === "appealing") pair.appealing = insight;
      else pair.improve = insight;
    }
  }

  return (
    <div className="bg-darpan-surface border border-darpan-border rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-darpan-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-darpan-cyan/10 flex items-center justify-center">
            <MessageSquare className="w-4 h-4 text-darpan-cyan" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">
              Qualitative Insights
            </h3>
            <p className="text-xs text-white/35">
              {loading
                ? "Generating AI analysis..."
                : error
                  ? "Showing raw responses (AI unavailable)"
                  : data?.cached
                    ? "AI-generated themes (cached)"
                    : "AI-generated themes"}
            </p>
          </div>
        </div>
        {!loading && data && (
          <button
            onClick={() => {
              toast.info("Regenerating insights...");
              fetchInsights(true);
            }}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-white/25 hover:text-white/50 hover:bg-white/5 transition-colors"
            title="Regenerate insights"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span className="text-xs">Refresh</span>
          </button>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <Loader2 className="w-5 h-5 text-darpan-cyan/50 animate-spin" />
            <p className="text-xs text-white/25">
              Analyzing open-ended responses with AI...
            </p>
          </div>
        ) : error || !data?.insights?.length ? (
          <RawEntries entries={entries} />
        ) : (
          <div className="space-y-3">
            {Array.from(insightsByConceptPair.entries()).map(
              ([cidx, { appealing, improve }]) => (
                <ConceptInsightCard
                  key={cidx}
                  appealing={appealing}
                  improve={improve}
                />
              ),
            )}
          </div>
        )}
      </div>
    </div>
  );
}
