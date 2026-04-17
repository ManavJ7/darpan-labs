/**
 * Ad Creative Testing Results Engine
 *
 * Computes Idea Strength Score (ISS) from twin simulation responses.
 * ISS = weighted composite of 4 metric groups (In-Market Impact, Engagement,
 * Brand Predisposition, Associations/Emotional Signature).
 * Weights adjust by campaign objective.
 */

import type { QuestionnaireSection, ConceptResponse } from "@/types/study";
import type { TwinSimulationResult } from "@/lib/studyApi";
import { getConceptName } from "@/lib/resultsEngine";

// ─── Types ─────────────────────────────────────────────

export interface MetricScore {
  value: number; // 0-100 normalized score
  rawMean: number;
  n: number;
}

export interface MetricGroupScores {
  groupName: string;
  metrics: Record<string, MetricScore>;
  groupScore: number; // 0-100 aggregate
}

export interface EmotionalProfile {
  active_positive: Record<string, number>; // descriptor → mean (1-5)
  passive_positive: Record<string, number>;
  passive_negative: Record<string, number>;
  active_negative: Record<string, number>;
}

export interface TerritoryResult {
  territoryIndex: number;
  territoryName: string;
  iss: number; // Idea Strength Score 0-100
  verdict: "develop" | "refine" | "park";
  groups: {
    in_market_impact: MetricGroupScores;
    engagement: MetricGroupScores;
    brand_predisposition: MetricGroupScores;
    associations: MetricGroupScores;
  };
  emotionalProfile: EmotionalProfile;
  qualitative: { question: string; answers: string[] }[];
}

export interface AdCreativeResults {
  territories: TerritoryResult[];
  availableMetrics: string[];
}

// ─── ISS Weights by Campaign Objective ─────────────────

const ISS_WEIGHTS: Record<string, Record<string, number>> = {
  default:              { in_market_impact: 0.30, engagement: 0.25, brand_predisposition: 0.30, associations: 0.15 },
  brand_building:       { in_market_impact: 0.25, engagement: 0.25, brand_predisposition: 0.30, associations: 0.20 },
  product_launch:       { in_market_impact: 0.35, engagement: 0.20, brand_predisposition: 0.35, associations: 0.10 },
  promotional_tactical: { in_market_impact: 0.40, engagement: 0.20, brand_predisposition: 0.30, associations: 0.10 },
  repositioning:        { in_market_impact: 0.25, engagement: 0.20, brand_predisposition: 0.30, associations: 0.25 },
  awareness:            { in_market_impact: 0.35, engagement: 0.25, brand_predisposition: 0.25, associations: 0.15 },
  category_entry:       { in_market_impact: 0.30, engagement: 0.25, brand_predisposition: 0.30, associations: 0.15 },
};

// ─── Metric → Group mapping ────────────────────────────

const METRIC_GROUPS: Record<string, string> = {
  // Group A: In-Market Impact
  communication_awareness: "in_market_impact",
  branded_memorability: "in_market_impact",
  distinctive_impact: "in_market_impact",
  misattribution_risk: "in_market_impact",
  freshness: "in_market_impact",
  memorability: "in_market_impact",
  originality: "in_market_impact",
  stopping_power_m1: "in_market_impact",
  // Group B: Engagement
  enjoyment: "engagement",
  involvement: "engagement",
  stopping_power: "engagement",
  relevance: "engagement",
  need_alignment: "engagement",
  // Group C: Brand Predisposition
  persuasion_lift: "brand_predisposition",
  brand_fit: "brand_predisposition",
  affinity: "brand_predisposition",
  advocacy: "brand_predisposition",
  personality_match: "brand_predisposition",
  // Group D: Associations (emotional)
  emotional_active_positive: "associations",
  emotional_passive_positive: "associations",
  emotional_passive_negative: "associations",
  emotional_active_negative: "associations",
};

const GROUP_LABELS: Record<string, string> = {
  in_market_impact: "In-Market Impact",
  engagement: "Engagement",
  brand_predisposition: "Brand Predisposition",
  associations: "Emotional Signature",
};

// ─── Metric Labels ─────────────────────────────────────

export const AD_METRIC_LABELS: Record<string, string> = {
  communication_awareness: "Communication Awareness",
  branded_memorability: "Branded Memorability",
  distinctive_impact: "Distinctive Impact",
  misattribution_risk: "Misattribution Risk",
  freshness: "Freshness",
  memorability: "Memorability",
  originality: "Originality",
  stopping_power_m1: "Stopping Power",
  enjoyment: "Enjoyment",
  involvement: "Involvement",
  stopping_power: "Stopping Power",
  relevance: "Relevance",
  need_alignment: "Need Alignment",
  persuasion_lift: "Persuasion Lift",
  brand_fit: "Brand Fit",
  affinity: "Affinity",
  advocacy: "Advocacy",
  personality_match: "Personality Match",
  emotional_active_positive: "Active Positive",
  emotional_passive_positive: "Passive Positive",
  emotional_passive_negative: "Passive Negative",
  emotional_active_negative: "Active Negative",
};

export function adMetricLabel(id: string): string {
  return AD_METRIC_LABELS[id] || id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Verdict ───────────────────────────────────────────

export function issVerdict(score: number): "develop" | "refine" | "park" {
  if (score >= 70) return "develop";
  if (score >= 50) return "refine";
  return "park";
}

export function verdictColor(v: string) {
  switch (v) {
    case "develop": return { text: "text-green-400", bg: "bg-green-400/10", border: "border-green-400/30" };
    case "refine": return { text: "text-amber-400", bg: "bg-amber-400/10", border: "border-amber-400/30" };
    case "park": return { text: "text-red-400", bg: "bg-red-400/10", border: "border-red-400/30" };
    default: return { text: "text-white/40", bg: "bg-white/5", border: "border-white/10" };
  }
}

// ─── Score color (metric tile) ─────────────────────────

export function scoreColor(value: number, lowerIsBetter = false): string {
  const v = lowerIsBetter ? 100 - value : value;
  if (v >= 70) return "#00FF88";
  if (v >= 50) return "#FFB800";
  return "#FF4444";
}

export function scoreBg(value: number, lowerIsBetter = false): string {
  const v = lowerIsBetter ? 100 - value : value;
  if (v >= 70) return "rgba(0,255,136,0.08)";
  if (v >= 50) return "rgba(255,184,0,0.08)";
  return "rgba(255,68,68,0.08)";
}

// ─── Answer parsing ────────────────────────────────────

const TEXT_TO_VALUE: Record<string, number> = {
  definitely_buy: 1, probably_buy: 2, might_buy: 3, probably_not: 4, definitely_not: 5,
  extremely: 1, very: 2, somewhat: 3, not_very: 4, not_at_all: 5,
  strongly_agree: 1, agree: 2, neither: 3, disagree: 4, strongly_disagree: 5,
  yes: 1, no: 5,
};

function parseAnswer(structured: unknown): number | null {
  if (typeof structured === "number") return structured;
  if (typeof structured === "string") {
    const n = parseFloat(structured);
    if (!isNaN(n)) return n;
    const normalized = structured.toLowerCase().replace(/[\s-]+/g, "_");
    if (normalized in TEXT_TO_VALUE) return TEXT_TO_VALUE[normalized];
    for (const [key, val] of Object.entries(TEXT_TO_VALUE)) {
      if (normalized.includes(key)) return val;
    }
  }
  if (structured && typeof structured === "object" && "value" in structured) {
    return parseAnswer((structured as Record<string, unknown>).value);
  }
  return null;
}

// ─── Normalize to 0-100 ────────────────────────────────

function normalizeScore(mean: number, scaleMin = 1, scaleMax = 5): number {
  return Math.round(((mean - scaleMin) / (scaleMax - scaleMin)) * 100);
}

// ─── Concept-section mapping (reuses pattern from resultsEngine) ──

function parseTerritoryIndex(sectionId: string, validIndices: Set<number>): number {
  // Match ANY section whose id ends in `_N` — covers M1_distinctiveness_1,
  // S3_territory_1, S4_unaided_recall_1, S5_aided_branding_1, etc.
  // Non-territory sections (S1_screening, S2_pre_exposure_baseline, S8_demographics)
  // correctly fall through to -1 since they have no trailing _N.
  const match = sectionId.match(/_(\d+)$/);
  if (!match) return -1;
  const n = parseInt(match[1], 10);
  if (isNaN(n)) return -1;
  if (validIndices.has(n)) return n;
  if (validIndices.has(n - 1)) return n - 1;
  return -1;
}

// ─── Main Processing ──────────────────────────────────

export function processAdCreativeResults(
  simResults: TwinSimulationResult[],
  sections: QuestionnaireSection[],
  concepts: ConceptResponse[],
  campaignObjective: string,
): AdCreativeResults {
  const validIndices = new Set(concepts.map((c) => c.concept_index));

  // Build question mapping: question_id → { metricId, territoryIndex }
  interface QMap { metricId: string | null; territoryIndex: number; questionType: string; questionText: string }
  const qMap = new Map<string, QMap>();

  for (const section of sections) {
    const tidx = parseTerritoryIndex(section.section_id, validIndices);
    for (const q of section.questions) {
      const qText = q.question_text?.en || q.question_text?.default || Object.values(q.question_text)[0] || "";
      qMap.set(q.question_id, {
        metricId: q.metric_id || null,
        territoryIndex: tidx,
        questionType: q.question_type,
        questionText: qText,
      });
    }
  }

  // Accumulate answers: territoryIndex → metricId → number[]
  const scoreAcc = new Map<number, Map<string, number[]>>();
  const qualAcc = new Map<string, { tidx: number; question: string; texts: string[] }>();

  const completed = simResults.filter((r) => r.status === "completed");
  for (const result of completed) {
    if (!result.responses) continue;
    for (const resp of result.responses as any[]) {
      if (resp.skipped) continue;
      const q = qMap.get(resp.question_id);
      if (!q || q.territoryIndex === -1) continue;

      if (q.metricId && (q.questionType === "rating" || q.questionType === "single_select")) {
        const val = parseAnswer(resp.structured_answer);
        if (val !== null) {
          if (!scoreAcc.has(q.territoryIndex)) scoreAcc.set(q.territoryIndex, new Map());
          const mm = scoreAcc.get(q.territoryIndex)!;
          if (!mm.has(q.metricId)) mm.set(q.metricId, []);
          mm.get(q.metricId)!.push(val);
        }
      }

      if (q.questionType === "open_text" && resp.structured_answer) {
        const text = typeof resp.structured_answer === "string" ? resp.structured_answer : JSON.stringify(resp.structured_answer);
        const key = `${resp.question_id}__${q.territoryIndex}`;
        if (!qualAcc.has(key)) qualAcc.set(key, { tidx: q.territoryIndex, question: resp.question_text || q.questionText, texts: [] });
        qualAcc.get(key)!.texts.push(text);
      }
    }
  }

  // Build territory results
  const weights = ISS_WEIGHTS[campaignObjective] || ISS_WEIGHTS.default;
  const conceptNames = new Map(concepts.map((c) => [c.concept_index, getConceptName(c)]));
  const allMetrics = new Set<string>();

  const territories: TerritoryResult[] = [];
  for (const concept of concepts) {
    const tidx = concept.concept_index;
    const mm = scoreAcc.get(tidx);

    // Calculate per-metric scores
    const metricScores = new Map<string, MetricScore>();
    if (mm) {
      for (const [metricId, answers] of mm) {
        allMetrics.add(metricId);
        const mean = answers.reduce((s, v) => s + v, 0) / answers.length;
        const lowerBetter = metricId === "misattribution_risk";
        const normalized = lowerBetter ? 100 - normalizeScore(mean) : normalizeScore(mean);
        metricScores.set(metricId, { value: normalized, rawMean: Math.round(mean * 100) / 100, n: answers.length });
      }
    }

    // Group metrics
    const groupScores: Record<string, { metrics: Record<string, MetricScore>; total: number; count: number }> = {
      in_market_impact: { metrics: {}, total: 0, count: 0 },
      engagement: { metrics: {}, total: 0, count: 0 },
      brand_predisposition: { metrics: {}, total: 0, count: 0 },
      associations: { metrics: {}, total: 0, count: 0 },
    };

    for (const [metricId, score] of metricScores) {
      const group = METRIC_GROUPS[metricId];
      if (group && groupScores[group]) {
        groupScores[group].metrics[metricId] = score;
        groupScores[group].total += score.value;
        groupScores[group].count += 1;
      }
    }

    const groups = Object.fromEntries(
      Object.entries(groupScores).map(([gid, g]) => [
        gid,
        {
          groupName: GROUP_LABELS[gid] || gid,
          metrics: g.metrics,
          groupScore: g.count > 0 ? Math.round(g.total / g.count) : 0,
        },
      ]),
    ) as TerritoryResult["groups"];

    // ISS = weighted sum of group scores
    let iss = 0;
    for (const [gid, weight] of Object.entries(weights)) {
      const gs = groups[gid as keyof typeof groups];
      if (gs) iss += gs.groupScore * weight;
    }
    iss = Math.round(iss);

    // Emotional profile
    const emotionalProfile: EmotionalProfile = {
      active_positive: {},
      passive_positive: {},
      passive_negative: {},
      active_negative: {},
    };
    // Extract from emotional descriptor metrics if available
    for (const [metricId, score] of metricScores) {
      if (metricId.startsWith("emotional_")) {
        const quadrant = metricId.replace("emotional_", "") as keyof EmotionalProfile;
        if (emotionalProfile[quadrant] !== undefined) {
          emotionalProfile[quadrant][metricId] = score.rawMean;
        }
      }
    }

    // Qualitative
    const qualitative: { question: string; answers: string[] }[] = [];
    for (const [, entry] of qualAcc) {
      if (entry.tidx === tidx) {
        qualitative.push({ question: entry.question, answers: entry.texts });
      }
    }

    territories.push({
      territoryIndex: tidx,
      territoryName: conceptNames.get(tidx) || `Territory ${tidx}`,
      iss,
      // Verdict is re-assigned below on a rank basis (see below). We set a
      // placeholder here so the type is satisfied at push time.
      verdict: "park",
      groups,
      emotionalProfile,
      qualitative,
    });
  }

  territories.sort((a, b) => b.iss - a.iss);

  // Rank-based verdict: the study brief dictates how many creatives to
  // develop (e.g. "I have budget to develop only one"). Rather than judging
  // every territory against an absolute ISS threshold — which produced the
  // "recommend all three" bug when scores clustered high — we just rank by
  // ISS and flag the top creative(s). All others are "not recommended" in
  // the context of this study, regardless of absolute score.
  territories.forEach((t, i) => {
    // Default develop-count is 1 — matches the most common ad-creative budget
    // constraint. Surface this through a study-level setting in a future pass.
    const topPickCount = 1;
    t.verdict = i < topPickCount ? "develop" : "park";
  });

  return { territories, availableMetrics: Array.from(allMetrics) };
}
