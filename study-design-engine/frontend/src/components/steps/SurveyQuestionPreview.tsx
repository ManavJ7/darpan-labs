"use client";

import { Badge } from "@/components/ui/Badge";
import { formatLabel } from "@/lib/utils";
import type { Question, ConceptResponse } from "@/types/study";

// ── Constants ────────────────────────────────────────────────────────

const COMPONENT_KEYS = [
  "consumer_insight",
  "product_name",
  "key_benefit",
  "reasons_to_believe",
  "visual",
  "price_format",
] as const;

type ScaleOption = { value: number | string; label: string };

// ── Scale helpers ────────────────────────────────────────────────────

/** Build a default 1-N point scale when the LLM omits options. */
function defaultScale(n = 5): ScaleOption[] {
  return Array.from({ length: n }, (_, i) => ({ value: i + 1, label: String(i + 1) }));
}

/** Default Likert-5 labels used when the LLM provides no option labels. */
const LIKERT_5_LABELS: Record<number, string> = {
  1: "Strongly disagree",
  2: "Disagree",
  3: "Neutral",
  4: "Agree",
  5: "Strongly agree",
};

/** Resolve anchors from various LLM formats. */
function resolveAnchors(
  anchors: Record<string, string> | null | undefined,
  numPoints: number,
): { low: string; high: string } {
  if (!anchors) return { low: "", high: "" };
  const low = anchors.low || anchors["1"] || "";
  const high = anchors.high || anchors[String(numPoints)] || "";
  return { low, high };
}

/**
 * Classify the scale type string into a normalized category.
 * The LLM can return many variants — we normalise them here once.
 */
function classifyScaleType(raw: string): "semantic" | "likert" | "importance" | "performance" | "generic" {
  const s = raw.toLowerCase();
  if (s.includes("semantic") || s.includes("differential") || s.includes("bipolar")) return "semantic";
  if (s.includes("likert")) return "likert";
  if (s.includes("importance")) return "importance";
  if (s.includes("performance")) return "performance";
  return "generic";
}

// ── Props ────────────────────────────────────────────────────────────

interface SurveyQuestionPreviewProps {
  question: Question;
  concepts: ConceptResponse[];
  /** When set, concept_exposure questions render only this concept (0-indexed). */
  conceptIndex?: number;
}

// ── Main Component ───────────────────────────────────────────────────

export function SurveyQuestionPreview({
  question,
  concepts,
  conceptIndex,
}: SurveyQuestionPreviewProps) {
  const questionText =
    question.question_text?.en || Object.values(question.question_text || {})[0] || "—";
  const options: ScaleOption[] = question.scale?.options || [];
  const anchors = question.scale?.anchors ?? null;
  const scaleType = question.scale?.type || "";
  const attributePairs = (question.scale as unknown as Record<string, unknown>)
    ?.attribute_pairs as Array<{ left: string; right: string }> | undefined;

  return (
    <div className="rounded-xl border border-darpan-border bg-darpan-surface/50 p-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-white/30 font-mono">
              Q{question.position_in_section}
            </span>
            {question.required && (
              <span className="text-red-400 text-xs">Required</span>
            )}
          </div>
          <p className="text-sm text-white/90 leading-relaxed">{questionText}</p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <Badge variant="default">{formatLabel(question.question_type)}</Badge>
          {scaleType && <Badge variant="cyan">{scaleType}</Badge>}
        </div>
      </div>

      {/* Show-if logic */}
      {question.show_if && (
        <p className="text-xs text-purple-400/60 mb-2">Show if: {question.show_if}</p>
      )}

      {/* Design notes */}
      {question.design_notes && (
        <p className="text-xs text-white/30 italic mb-3">{question.design_notes}</p>
      )}

      {/* Response control */}
      <div className="mt-2">
        <ResponseControl
          questionType={question.question_type}
          options={options}
          anchors={anchors}
          scaleType={scaleType}
          attributePairs={attributePairs}
          concepts={concepts}
          conceptIndex={conceptIndex}
        />
      </div>
    </div>
  );
}

// ── Response Control Router ──────────────────────────────────────────

function ResponseControl({
  questionType,
  options,
  anchors,
  scaleType,
  attributePairs,
  concepts,
  conceptIndex,
}: {
  questionType: string;
  options: ScaleOption[];
  anchors: Record<string, string> | null;
  scaleType: string;
  attributePairs?: Array<{ left: string; right: string }>;
  concepts: ConceptResponse[];
  conceptIndex?: number;
}) {
  switch (questionType) {
    case "single_select":
      return <OptionListPreview options={options} shape="circle" />;

    case "multi_select":
      return <OptionListPreview options={options} shape="square" />;

    case "open_text":
      return <OpenTextPreview />;

    case "rating":
      return (
        <RatingRouter
          options={options}
          anchors={anchors}
          scaleType={scaleType}
          attributePairs={attributePairs}
        />
      );

    case "ranking":
      return <RankingPreview options={options} />;

    case "concept_exposure":
      return (
        <ConceptExposurePreview
          concepts={conceptIndex != null ? [concepts[conceptIndex]].filter(Boolean) : concepts}
        />
      );

    default:
      // Fallback: if options exist show as radio, else show text box
      return options.length > 0
        ? <OptionListPreview options={options} shape="circle" />
        : <OpenTextPreview />;
  }
}

// ── Single / Multi Select ────────────────────────────────────────────

function OptionListPreview({
  options,
  shape,
}: {
  options: ScaleOption[];
  shape: "circle" | "square";
}) {
  if (options.length === 0) {
    return <EmptyNotice text="No options defined — add options via the editor." />;
  }
  const shapeClass = shape === "circle" ? "rounded-full" : "rounded";
  return (
    <div className="space-y-2">
      {options.map((opt) => (
        <label key={opt.value} className="flex items-center gap-2.5 cursor-default">
          <span className={`w-4 h-4 border border-white/20 shrink-0 ${shapeClass}`} />
          <span className="text-sm text-white/60">{opt.label}</span>
        </label>
      ))}
    </div>
  );
}

// ── Open Text ────────────────────────────────────────────────────────

function OpenTextPreview() {
  return (
    <textarea
      disabled
      placeholder="Respondent types their answer here..."
      className="w-full h-20 px-3 py-2 bg-darpan-bg/50 border border-darpan-border rounded-lg text-sm text-white/30 placeholder-white/20 resize-none cursor-default"
    />
  );
}

// ── Rating Router ────────────────────────────────────────────────────
// Dispatches to the correct sub-renderer based on scale type.

function RatingRouter({
  options,
  anchors,
  scaleType,
  attributePairs,
}: {
  options: ScaleOption[];
  anchors: Record<string, string> | null;
  scaleType: string;
  attributePairs?: Array<{ left: string; right: string }>;
}) {
  const kind = classifyScaleType(scaleType);

  switch (kind) {
    case "semantic":
      return (
        <SemanticDifferentialPreview
          options={options}
          anchors={anchors}
          attributePairs={attributePairs}
        />
      );
    case "importance":
      return <GridRatingPreview options={options} anchors={anchors} label="importance" />;
    case "performance":
      return <GridRatingPreview options={options} anchors={anchors} label="performance" />;
    case "likert":
      return <LikertPreview options={options} anchors={anchors} />;
    default:
      return <GenericRatingPreview options={options} anchors={anchors} />;
  }
}

// ── Likert Scale ─────────────────────────────────────────────────────

function LikertPreview({
  options,
  anchors,
}: {
  options: ScaleOption[];
  anchors: Record<string, string> | null;
}) {
  // Use provided options, or generate labeled 5-point Likert defaults
  const pts: ScaleOption[] =
    options.length > 0
      ? options
      : defaultScale(5).map((p) => ({
          value: p.value,
          label: LIKERT_5_LABELS[p.value as number] || String(p.value),
        }));

  const { low, high } = resolveAnchors(anchors, pts.length);

  return (
    <div>
      {(low || high) && <AnchorBar low={low} high={high} />}
      <ScaleCircles points={pts} />
    </div>
  );
}

// ── Generic Rating (numbered scale) ─────────────────────────────────

function GenericRatingPreview({
  options,
  anchors,
}: {
  options: ScaleOption[];
  anchors: Record<string, string> | null;
}) {
  const pts = options.length > 0 ? options : defaultScale(5);
  const { low, high } = resolveAnchors(anchors, pts.length);

  return (
    <div>
      {(low || high) && <AnchorBar low={low} high={high} />}
      <ScaleCircles points={pts} />
    </div>
  );
}

// ── Grid Rating (importance / performance) ───────────────────────────
// These are matrix-style questions where multiple items are rated on a
// single scale. The LLM often omits the items — we show the scale with
// a note explaining the format.

function GridRatingPreview({
  options,
  anchors,
  label,
}: {
  options: ScaleOption[];
  anchors: Record<string, string> | null;
  label: "importance" | "performance";
}) {
  const pts = options.length > 0 ? options : defaultScale(5);
  const { low, high } = resolveAnchors(anchors, pts.length);

  const defaultAnchors: Record<string, { low: string; high: string }> = {
    importance: { low: "Not at all important", high: "Extremely important" },
    performance: { low: "Very poor", high: "Excellent" },
  };
  const effectiveLow = low || defaultAnchors[label].low;
  const effectiveHigh = high || defaultAnchors[label].high;

  return (
    <div className="space-y-2">
      <p className="text-xs text-white/40 italic">
        Grid question — each attribute is rated on the scale below.
      </p>
      <AnchorBar low={effectiveLow} high={effectiveHigh} />
      <ScaleCircles points={pts} />
    </div>
  );
}

// ── Semantic Differential ────────────────────────────────────────────

function SemanticDifferentialPreview({
  options,
  anchors,
  attributePairs,
}: {
  options: ScaleOption[];
  anchors: Record<string, string> | null;
  attributePairs?: Array<{ left: string; right: string }>;
}) {
  const pts = options.length > 0 ? options : defaultScale(5);

  // Build rows from attribute_pairs, anchors, or show placeholder
  let rows: Array<{ left: string; right: string }> = [];

  if (attributePairs && attributePairs.length > 0) {
    rows = attributePairs;
  } else if (anchors) {
    const keys = Object.keys(anchors).sort();
    const left = anchors.low || (keys.length > 0 ? anchors[keys[0]] : "") || "";
    const right = anchors.high || (keys.length > 1 ? anchors[keys[keys.length - 1]] : "") || "";
    if (left || right) rows = [{ left, right }];
  }

  if (rows.length === 0) {
    return (
      <div className="space-y-2">
        <p className="text-xs text-white/40 italic">
          Semantic differential — each row shows a bipolar adjective pair rated on the scale below.
        </p>
        <div className="flex items-center gap-3">
          <span className="text-xs text-white/30 min-w-[80px] text-right">‹ Left anchor ›</span>
          <div className="flex items-center gap-1.5">
            {pts.map((pt) => (
              <span
                key={pt.value}
                className="w-8 h-8 rounded-full border border-white/20 flex items-center justify-center text-[10px] text-white/30 font-mono"
              >
                {pt.value}
              </span>
            ))}
          </div>
          <span className="text-xs text-white/30 min-w-[80px]">‹ Right anchor ›</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {rows.map((pair, i) => (
        <div key={i} className="flex items-center gap-3">
          <span className="text-xs text-white/50 font-medium min-w-[80px] text-right shrink-0">
            {pair.left}
          </span>
          <div className="flex items-center gap-1.5">
            {pts.map((pt) => (
              <span
                key={pt.value}
                className="w-8 h-8 rounded-full border border-white/20 flex items-center justify-center text-[10px] text-white/30 font-mono"
              >
                {pt.value}
              </span>
            ))}
          </div>
          <span className="text-xs text-white/50 font-medium min-w-[80px] shrink-0">
            {pair.right}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Ranking ──────────────────────────────────────────────────────────

function RankingPreview({ options }: { options: ScaleOption[] }) {
  if (options.length === 0) {
    return <EmptyNotice text="No items to rank — add options via the editor." />;
  }
  return (
    <div className="space-y-1.5">
      {options.map((opt, i) => (
        <div
          key={opt.value}
          className="flex items-center gap-3 px-3 py-2 bg-darpan-bg/30 border border-darpan-border/50 rounded-lg"
        >
          <span className="text-xs text-white/30 font-mono w-5">{i + 1}.</span>
          <span className="text-xs text-white/20 cursor-grab">&#x2807;</span>
          <span className="text-sm text-white/60">{opt.label}</span>
        </div>
      ))}
    </div>
  );
}

// ── Concept Exposure ─────────────────────────────────────────────────

function ConceptExposurePreview({ concepts }: { concepts: ConceptResponse[] }) {
  if (concepts.length === 0) {
    return <p className="text-sm text-white/30 italic">Loading concepts...</p>;
  }

  return (
    <div className="space-y-4">
      {concepts.map((concept, idx) => (
        <div
          key={concept.id}
          className="rounded-lg border border-darpan-border bg-darpan-bg/40 p-4"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-white/70">Concept {idx + 1}</span>
            <Badge variant={concept.status === "approved" ? "approved" : "draft"}>
              {formatLabel(concept.status)}
            </Badge>
          </div>

          {concept.image_url && (
            <div className="mb-3 rounded-lg overflow-hidden border border-darpan-border/50">
              <img
                src={concept.image_url}
                alt={`Concept ${idx + 1}`}
                className="w-full h-auto max-h-48 object-contain bg-white/5"
              />
            </div>
          )}

          <div className="space-y-2">
            {COMPONENT_KEYS.map((key) => {
              const comp = (concept.components as Record<string, unknown>)[key] as
                | Record<string, unknown>
                | undefined;
              if (!comp) return null;

              const rawInput = (comp.raw_input || comp.description || comp.price) as
                | string
                | undefined;
              const refined = (comp.refined || comp.refined_description || comp.refined_price) as
                | string
                | undefined;
              const brandEdit = comp.brand_edit as string | undefined;
              const displayText = brandEdit || refined || rawInput;

              if (!displayText) return null;

              return (
                <div key={key} className="flex gap-2">
                  <span className="text-xs text-white/30 w-32 shrink-0 pt-0.5">
                    {formatLabel(key)}
                  </span>
                  <span className="text-sm text-white/60">{displayText}</span>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Shared Sub-components ────────────────────────────────────────────

function AnchorBar({ low, high }: { low: string; high: string }) {
  return (
    <div className="flex justify-between text-xs text-white/30 mb-2">
      <span>{low}</span>
      <span>{high}</span>
    </div>
  );
}

function ScaleCircles({ points }: { points: ScaleOption[] }) {
  return (
    <div className="flex items-start gap-2 flex-wrap">
      {points.map((pt) => (
        <div key={pt.value} className="flex flex-col items-center gap-1">
          <span className="w-9 h-9 rounded-full border border-white/20 flex items-center justify-center text-xs text-white/40 font-mono">
            {pt.value}
          </span>
          {pt.label && pt.label !== String(pt.value) && (
            <span className="text-[10px] text-white/30 text-center max-w-[60px] leading-tight">
              {pt.label}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function EmptyNotice({ text }: { text: string }) {
  return <p className="text-xs text-white/25 italic">{text}</p>;
}
