import type {
  QuestionnaireSection,
  Question,
  ConceptResponse,
} from "@/types/study";
import type { TwinSimulationResult } from "@/lib/studyApi";

// ─── Types ─────────────────────────────────────────────

export interface T2BScore {
  t2b: number; // Top-2-Box %
  mean: number;
  n: number;
}

export interface ConceptScoreRow {
  conceptIndex: number;
  conceptName: string;
  metrics: Record<string, T2BScore>;
  aggregate: number;
}

export interface QualitativeEntry {
  questionText: string;
  conceptIndex: number;
  conceptName: string;
  answers: string[];
}

export interface ProcessedResults {
  scoreRows: ConceptScoreRow[];
  qualitativeEntries: QualitativeEntry[];
  availableTwins: { id: string; externalId: string }[];
  availableConcepts: { index: number; name: string }[];
  availableMetrics: { id: string; label: string }[];
}

// ─── Metric labels ─────────────────────────────────────

const METRIC_LABELS: Record<string, string> = {
  pi: "Purchase Intent",
  purchase_intent: "Purchase Intent",
  uniqueness: "Uniqueness",
  relevance: "Relevance",
  believability: "Believability",
  interest: "Interest",
  brand_fit: "Brand Fit",
  routine_fit: "Routine Fit",
  time_saving: "Time Saving",
  appeal: "Appeal",
  value: "Value",
  likelihood: "Likelihood",
  satisfaction: "Satisfaction",
  recommendation: "Recommendation",
};

export function metricLabel(id: string): string {
  return (
    METRIC_LABELS[id] ||
    id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

// ─── Concept name helper ───────────────────────────────

export function getConceptName(c: ConceptResponse): string {
  const comp = c.components as Record<string, any>;
  return (
    // Ad-creative territory shape (brand_edit wins, then refined, then raw)
    comp?.territory_name?.brand_edit ||
    comp?.territory_name?.refined ||
    comp?.territory_name?.raw_input ||
    // Concept-testing product shape
    comp?.product_name?.brand_edit ||
    comp?.product_name?.refined ||
    comp?.product_name?.raw_input ||
    // Fallback — concept_index is already 1-indexed in the DB
    `Concept ${c.concept_index}`
  );
}

// ─── Infer metric from question text ───────────────────

const METRIC_PATTERNS: [RegExp, string][] = [
  [/how likely.*(?:buy|purchase)/i, "purchase_intent"],
  [/how interested/i, "interest"],
  [/how unique|how different/i, "uniqueness"],
  [/how relevant/i, "relevance"],
  [/how believable/i, "believability"],
  [/fit with.*(?:brand|expect from)/i, "brand_fit"],
  [/fit with.*(?:routine|current)/i, "routine_fit"],
  [/save.*time/i, "time_saving"],
  [/how appealing|overall appeal/i, "appeal"],
];

function inferMetric(questionText: string): string | null {
  for (const [pattern, metricId] of METRIC_PATTERNS) {
    if (pattern.test(questionText)) return metricId;
  }
  return null;
}

// ─── Map text answers to numeric values ────────────────
//
// Categorical single_select answers are text labels (e.g. "probably_buy", "very").
// The scale options use value 1 = best, 5 = worst.
// We normalize all answers to a 1-5 scale where 1 = best.

const TEXT_TO_VALUE: Record<string, number> = {
  // Purchase intent
  definitely_buy: 1, definitely: 1,
  probably_buy: 2, probably: 2,
  might_buy: 3, might: 3,
  probably_not: 4,
  definitely_not: 5,
  // Intensity scale (uniqueness, relevance, believability, etc.)
  extremely: 1,
  very: 2,
  somewhat: 3,
  not_very: 4,
  not_at_all: 5,
  // Brand fit
  fits_extremely: 1,
  fits_very: 2,
  fits_somewhat: 3,
  doesnt_fit_very: 4,
  doesnt_fit: 5,
  // Satisfaction (fallback)
  very_satisfied: 1,
  satisfied: 2,
  neutral: 3,
  dissatisfied: 4,
  very_dissatisfied: 5,
  // Agreement
  strongly_agree: 1,
  agree: 2,
  neither: 3,
  disagree: 4,
  strongly_disagree: 5,
};

/**
 * Parse a structured_answer into a normalized 1-5 value.
 * - Numeric answers are returned as-is
 * - Text labels are mapped via TEXT_TO_VALUE
 */
function parseAnswer(structured: unknown): number | null {
  if (typeof structured === "number") return structured;
  if (typeof structured === "string") {
    // Try numeric first
    const n = parseFloat(structured);
    if (!isNaN(n)) return n;
    // Try text label lookup
    const normalized = structured.toLowerCase().replace(/[\s-]+/g, "_");
    if (normalized in TEXT_TO_VALUE) return TEXT_TO_VALUE[normalized];
    // Partial match: check if any key is contained in the answer
    for (const [key, val] of Object.entries(TEXT_TO_VALUE)) {
      if (normalized.includes(key)) return val;
    }
    return null;
  }
  if (structured && typeof structured === "object" && "value" in structured) {
    return parseAnswer((structured as Record<string, unknown>).value);
  }
  return null;
}

// ─── Question → concept + metric mapping ───────────────

interface QuestionMapping {
  questionId: string;
  metricId: string | null;
  conceptIndex: number; // -1 = not concept-specific
  questionType: string;
  questionText: string;
  isScorable: boolean; // can compute T2B from this question
  scaleDirection: "higher_better" | "lower_better";
}

export function buildQuestionMapping(
  sections: QuestionnaireSection[],
  concepts: ConceptResponse[],
): Map<string, QuestionMapping> {
  const map = new Map<string, QuestionMapping>();
  const validIndices = new Set(concepts.map((c) => c.concept_index));

  for (const section of sections) {
    const conceptIdx = parseConceptFromSectionId(section.section_id, validIndices);

    for (const q of section.questions) {
      const qText =
        q.question_text?.en ||
        q.question_text?.default ||
        Object.values(q.question_text)[0] ||
        "";

      // Determine metric: use explicit metric_id, or infer from question text
      const metricId = q.metric_id || inferMetric(qText);

      // Determine if this question is scorable (produces a T2B-able value)
      const scaleType = q.scale?.type;
      const isRating =
        q.question_type === "scale" ||
        q.question_type === "likert" ||
        q.question_type === "rating";
      const isCategoricalSingleSelect =
        q.question_type === "single_select" && scaleType === "categorical";

      // Scorable = has a metric, and is either a rating or a categorical single_select
      // (but NOT multi_select, NOT semantic_differential)
      const isScorable =
        metricId !== null &&
        (isRating || isCategoricalSingleSelect) &&
        scaleType !== "semantic_differential";

      // Scale direction: rating/likert_5 → higher is better (5 = best)
      // categorical single_select → lower is better (1 = "Definitely would buy")
      const scaleDirection: "higher_better" | "lower_better" =
        isRating ? "higher_better" : "lower_better";

      map.set(q.question_id, {
        questionId: q.question_id,
        metricId,
        conceptIndex: conceptIdx,
        questionType: q.question_type,
        questionText: qText,
        isScorable,
        scaleDirection,
      });
    }
  }

  return map;
}

function parseConceptFromSectionId(
  sectionId: string,
  validIndices: Set<number>,
): number {
  const match = sectionId.match(/concept[_-](\d+)/i);
  if (!match) return -1;
  const n = parseInt(match[1], 10);
  if (isNaN(n)) return -1;
  // Try direct match first (concept_N → concept_index=N, 1-indexed)
  if (validIndices.has(n)) return n;
  // Fallback: zero-indexed (concept_1 → concept_index=0)
  if (validIndices.has(n - 1)) return n - 1;
  return -1;
}

// ─── Composite weights (same as validation dashboard) ──

// Composite = 35% PI + 25% Uniqueness + 20% Relevance + 20% Believability
const COMPOSITE_METRICS: [string, number][] = [
  ["purchase_intent", 0.35],
  ["uniqueness", 0.25],
  ["relevance", 0.20],
  ["believability", 0.20],
];

function computeComposite(metrics: Record<string, T2BScore>): number | null {
  let weightedSum = 0;
  let found = false;

  for (const [metricId, weight] of COMPOSITE_METRICS) {
    const score = metrics[metricId];
    if (score && score.n > 0) {
      weightedSum += score.t2b * weight;
      found = true;
    }
  }

  return found ? Math.round(weightedSum * 10) / 10 : null;
}

// ─── T2B calculation ───────────────────────────────────

/**
 * Compute T2B score.
 * - higher_better: T2B = % of answers >= 4 (on 1-5 scale, 5 = best)
 * - lower_better:  T2B = % of answers <= 2 (on 1-5 scale, 1 = best)
 */
function calcT2B(
  answers: number[],
  direction: "higher_better" | "lower_better",
): T2BScore {
  if (answers.length === 0) return { t2b: 0, mean: 0, n: 0 };

  const top2 =
    direction === "higher_better"
      ? answers.filter((a) => a >= 4).length
      : answers.filter((a) => a <= 2).length;

  const mean = answers.reduce((s, a) => s + a, 0) / answers.length;
  return {
    t2b: (top2 / answers.length) * 100,
    mean: Math.round(mean * 100) / 100,
    n: answers.length,
  };
}

// ─── Main processing ──────────────────────────────────

export function processResults(
  simResults: TwinSimulationResult[],
  sections: QuestionnaireSection[],
  concepts: ConceptResponse[],
  selectedTwinIds: Set<string>,
  selectedConceptIndices: Set<number>,
  selectedMetricIds: Set<string>,
): ProcessedResults {
  const mapping = buildQuestionMapping(sections, concepts);

  const conceptNames = concepts
    .map((c) => ({ index: c.concept_index, name: getConceptName(c) }))
    .sort((a, b) => a.index - b.index);

  // Available twins
  const availableTwins = simResults
    .filter((r) => r.status === "completed")
    .map((r) => ({ id: r.twin_id, externalId: r.twin_external_id }));

  // Discover all scorable metrics from questionnaire
  const allMetricIds = new Set<string>();
  const metricDirections = new Map<string, "higher_better" | "lower_better">();
  for (const [, m] of mapping) {
    if (m.metricId && m.isScorable) {
      allMetricIds.add(m.metricId);
      metricDirections.set(m.metricId, m.scaleDirection);
    }
  }
  const availableMetrics = Array.from(allMetricIds).map((id) => ({
    id,
    label: metricLabel(id),
  }));

  // Filter simulation results to selected twins
  const filtered = simResults.filter(
    (r) => r.status === "completed" && selectedTwinIds.has(r.twin_id),
  );

  // Accumulate: conceptIdx → metricId → number[]
  const scoreAcc = new Map<number, Map<string, number[]>>();
  const qualAcc = new Map<
    string,
    { conceptIndex: number; texts: string[]; questionText: string }
  >();

  for (const result of filtered) {
    if (!result.responses) continue;

    for (const resp of result.responses as any[]) {
      if (resp.skipped) continue;

      const qm = mapping.get(resp.question_id);
      if (!qm || qm.conceptIndex === -1) continue;
      if (!selectedConceptIndices.has(qm.conceptIndex)) continue;

      // Quantitative / scorable
      if (qm.isScorable && qm.metricId && selectedMetricIds.has(qm.metricId)) {
        const val = parseAnswer(resp.structured_answer);
        if (val !== null) {
          if (!scoreAcc.has(qm.conceptIndex))
            scoreAcc.set(qm.conceptIndex, new Map());
          const mm = scoreAcc.get(qm.conceptIndex)!;
          if (!mm.has(qm.metricId)) mm.set(qm.metricId, []);
          mm.get(qm.metricId)!.push(val);
        }
      }

      // Qualitative / open-end
      if (
        (qm.questionType === "open_end" ||
          qm.questionType === "open_ended" ||
          qm.questionType === "open_text" ||
          qm.questionType === "text") &&
        resp.structured_answer
      ) {
        const text =
          typeof resp.structured_answer === "string"
            ? resp.structured_answer
            : JSON.stringify(resp.structured_answer);
        const key = `${resp.question_id}__${qm.conceptIndex}`;
        if (!qualAcc.has(key)) {
          qualAcc.set(key, {
            conceptIndex: qm.conceptIndex,
            texts: [],
            questionText: resp.question_text || qm.questionText,
          });
        }
        qualAcc.get(key)!.texts.push(text);
      }
    }
  }

  // Build score rows
  const scoreRows: ConceptScoreRow[] = [];
  for (const concept of conceptNames) {
    if (!selectedConceptIndices.has(concept.index)) continue;

    const mm = scoreAcc.get(concept.index);
    const metrics: Record<string, T2BScore> = {};

    for (const mId of selectedMetricIds) {
      const answers = mm?.get(mId) || [];
      const direction = metricDirections.get(mId) || "higher_better";
      metrics[mId] = calcT2B(answers, direction);
    }

    const composite = computeComposite(metrics);

    scoreRows.push({
      conceptIndex: concept.index,
      conceptName: concept.name,
      metrics,
      aggregate: composite ?? 0,
    });
  }

  scoreRows.sort((a, b) => b.aggregate - a.aggregate);

  // Build qualitative entries
  const qualitativeEntries: QualitativeEntry[] = [];
  for (const [, entry] of qualAcc) {
    const concept = conceptNames.find((c) => c.index === entry.conceptIndex);
    if (!concept) continue;
    qualitativeEntries.push({
      questionText: entry.questionText,
      conceptIndex: entry.conceptIndex,
      conceptName: concept.name,
      answers: entry.texts,
    });
  }
  qualitativeEntries.sort((a, b) => a.conceptIndex - b.conceptIndex);

  return {
    scoreRows,
    qualitativeEntries,
    availableTwins,
    availableConcepts: conceptNames,
    availableMetrics,
  };
}

// ─── Recommendation ────────────────────────────────────

export function guessNumToSelect(question: string): number {
  const lower = question.toLowerCase();
  const wordToNum: Record<string, number> = {
    one: 1, two: 2, three: 3, four: 4, five: 5,
  };
  const patterns = [
    /(?:select|choose|pick|develop|launch|keep|go\s+with|narrow\s+(?:it\s+)?down\s+to)\s+(?:only\s+)?(\d+|one|two|three|four|five)/i,
    /budget\s+(?:for|to\s+\w+)\s+(?:only\s+)?(\d+|one|two|three|four|five)/i,
    /only\s+(\d+|one|two|three|four|five)\b/i,
  ];
  for (const pat of patterns) {
    const m = lower.match(pat);
    if (m) {
      const n = wordToNum[m[1]] ?? parseInt(m[1], 10);
      if (!isNaN(n) && n > 0) return n;
    }
  }
  return 1;
}

export function generateRecommendation(
  scoreRows: ConceptScoreRow[],
  numToSelect: number,
): { recommended: ConceptScoreRow[]; explanation: string } {
  const sorted = [...scoreRows].sort((a, b) => b.aggregate - a.aggregate);
  const recommended = sorted.slice(0, Math.min(numToSelect, sorted.length));

  if (recommended.length === 0) {
    return { recommended: [], explanation: "No scored concepts available." };
  }

  const names = recommended.map((r) => `**${r.conceptName}**`).join(", ");

  if (numToSelect === 1) {
    return {
      recommended,
      explanation: `${names} is the top concept with an average T2B of ${recommended[0].aggregate.toFixed(1)}%.`,
    };
  }

  return {
    recommended,
    explanation: `The top ${recommended.length} concepts are ${names}.`,
  };
}

// ─── Color utilities ───────────────────────────────────

export function t2bColor(value: number | null): string {
  if (value === null || value === 0) return "#666666";
  if (value >= 60) return "#00FF88";
  if (value >= 35) return "#FFB800";
  return "#FF4444";
}

export function t2bBg(value: number | null): string {
  if (value === null || value === 0) return "rgba(102,102,102,0.06)";
  if (value >= 60) return "rgba(0,255,136,0.08)";
  if (value >= 35) return "rgba(255,184,0,0.08)";
  return "rgba(255,68,68,0.08)";
}
