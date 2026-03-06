/**
 * Generates a print-ready HTML survey document in a new window.
 * Handles concept-question interleaving: pre-concept sections, then
 * per-concept blocks (concept board + per-concept questions), then post-concept sections.
 */

import type {
  QuestionnaireContent,
  QuestionnaireSection,
  Question,
  ConceptResponse,
} from "@/types/study";

const COMPONENT_KEYS = [
  "consumer_insight",
  "product_name",
  "key_benefit",
  "reasons_to_believe",
  "visual",
  "price_format",
] as const;

// ── Helpers ──────────────────────────────────────────────────────────

/** Section IDs that are always pre-concept. */
const PRE_CONCEPT_IDS = new Set(["S1_screening", "S2_category_context"]);
/** Section IDs that are always post-concept. */
const POST_CONCEPT_IDS = new Set(["S8_demographics"]);
/** Text patterns indicating a question is about "this product/concept". */
const CONCEPT_REF_RE = /\bthis (product|concept|item)\b|\bconcept\b|\bproduct shown\b/i;

function isConceptSpecificSection(section: QuestionnaireSection): boolean {
  if (section.questions.some((q) => q.question_type === "concept_exposure")) return true;
  return section.questions.some((q) => {
    const text = q.question_text?.en || Object.values(q.question_text || {})[0] || "";
    return CONCEPT_REF_RE.test(text);
  });
}

function esc(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function formatLabel(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function getConceptDisplayText(comp: Record<string, unknown>): string | null {
  const brandEdit = comp.brand_edit as string | undefined;
  const refined = (comp.refined || comp.refined_description || comp.refined_price) as string | undefined;
  const rawInput = (comp.raw_input || comp.description || comp.price) as string | undefined;
  return brandEdit || refined || rawInput || null;
}

type ScaleOption = { value: number | string; label: string };

function defaultScale(n = 5): ScaleOption[] {
  return Array.from({ length: n }, (_, i) => ({ value: i + 1, label: String(i + 1) }));
}

function resolveAnchors(
  anchors: Record<string, string> | undefined | null,
  numPoints: number,
): { low: string; high: string } {
  if (!anchors) return { low: "", high: "" };
  const low = anchors.low || anchors["1"] || "";
  const high = anchors.high || anchors[String(numPoints)] || "";
  return { low, high };
}

function classifyScaleType(raw: string): "semantic" | "likert" | "importance" | "performance" | "generic" {
  const s = raw.toLowerCase();
  if (s.includes("semantic") || s.includes("differential") || s.includes("bipolar")) return "semantic";
  if (s.includes("likert")) return "likert";
  if (s.includes("importance")) return "importance";
  if (s.includes("performance")) return "performance";
  return "generic";
}

const LIKERT_5_LABELS: Record<number, string> = {
  1: "Strongly disagree",
  2: "Disagree",
  3: "Neutral",
  4: "Agree",
  5: "Strongly agree",
};

const DEFAULT_ANCHORS: Record<string, { low: string; high: string }> = {
  importance: { low: "Not at all important", high: "Extremely important" },
  performance: { low: "Very poor", high: "Excellent" },
};

// ── Question HTML renderers ──────────────────────────────────────────

function renderQuestionHeader(q: Question, globalNum: number): string {
  const text = q.question_text?.en || Object.values(q.question_text || {})[0] || "—";
  const required = q.required ? ' <span class="required">*</span>' : "";
  const notes = q.design_notes ? `<div class="design-notes">${esc(q.design_notes)}</div>` : "";
  const showIf = q.show_if ? `<div class="show-if">Show if: ${esc(q.show_if)}</div>` : "";
  const typeBadge = `<span class="type-badge">${esc(formatLabel(q.question_type))}</span>`;
  const scaleBadge = q.scale?.type ? ` <span class="scale-badge">${esc(q.scale.type)}</span>` : "";

  return `
    <div class="question">
      <div class="q-header">
        <span class="q-num">Q${globalNum}</span>
        ${typeBadge}${scaleBadge}
        ${required}
      </div>
      <div class="q-text">${esc(text)}</div>
      ${showIf}
      ${notes}
      ${renderResponseControl(q)}
    </div>
  `;
}

function renderResponseControl(q: Question): string {
  const options: ScaleOption[] = q.scale?.options || [];
  const anchors = q.scale?.anchors;
  const scaleType = q.scale?.type || "";
  const attrPairs = (q.scale as unknown as Record<string, unknown>)?.attribute_pairs as
    | Array<{ left: string; right: string }>
    | undefined;

  switch (q.question_type) {
    case "single_select":
      return renderOptionList(options, "radio");
    case "multi_select":
      return renderOptionList(options, "checkbox");
    case "open_text":
      return '<div class="open-text-box">Respondent writes answer here...</div>';
    case "rating":
      return renderRating(options, anchors, scaleType, attrPairs);
    case "ranking":
      return renderRankingList(options);
    case "concept_exposure":
      return '<div class="concept-placeholder">[Concept board is shown above]</div>';
    default:
      return options.length > 0
        ? renderOptionList(options, "radio")
        : '<div class="open-text-box">Respondent provides answer here...</div>';
  }
}

function renderOptionList(options: ScaleOption[], kind: "radio" | "checkbox"): string {
  if (options.length === 0) return '<div class="no-scale">No options defined</div>';
  const shape = kind === "radio" ? "radio-circle" : "checkbox-square";
  return `<div class="options-list">${options
    .map((o) => `<div class="option"><span class="${shape}"></span> ${esc(o.label)}</div>`)
    .join("")}</div>`;
}

function renderRating(
  options: ScaleOption[],
  anchors: Record<string, string> | undefined,
  scaleType: string,
  attrPairs?: Array<{ left: string; right: string }>,
): string {
  const kind = classifyScaleType(scaleType);

  switch (kind) {
    case "semantic":
      return renderSemanticDifferential(options, anchors, attrPairs);
    case "importance":
    case "performance":
      return renderGridRating(options, anchors, kind);
    case "likert":
      return renderLikertScale(options, anchors);
    default:
      return renderGenericRating(options, anchors);
  }
}

function renderScaleCircles(pts: ScaleOption[]): string {
  return `<div class="rating-scale">${pts
    .map((o) => {
      const showLabel = o.label && o.label !== String(o.value);
      return `<div class="scale-point"><div class="scale-circle">${esc(String(o.value))}</div>${showLabel ? `<div class="scale-label">${esc(o.label)}</div>` : ""}</div>`;
    })
    .join("")}</div>`;
}

function renderAnchorRow(low: string, high: string): string {
  if (!low && !high) return "";
  return `<div class="anchor-row"><span>${esc(low)}</span><span>${esc(high)}</span></div>`;
}

function renderLikertScale(options: ScaleOption[], anchors?: Record<string, string>): string {
  const pts: ScaleOption[] =
    options.length > 0
      ? options
      : defaultScale(5).map((p) => ({
          value: p.value,
          label: LIKERT_5_LABELS[p.value as number] || String(p.value),
        }));
  const { low, high } = resolveAnchors(anchors, pts.length);
  return renderAnchorRow(low, high) + renderScaleCircles(pts);
}

function renderGenericRating(options: ScaleOption[], anchors?: Record<string, string>): string {
  const pts = options.length > 0 ? options : defaultScale(5);
  const { low, high } = resolveAnchors(anchors, pts.length);
  return renderAnchorRow(low, high) + renderScaleCircles(pts);
}

function renderGridRating(
  options: ScaleOption[],
  anchors: Record<string, string> | undefined,
  label: "importance" | "performance",
): string {
  const pts = options.length > 0 ? options : defaultScale(5);
  const { low, high } = resolveAnchors(anchors, pts.length);
  const effectiveLow = low || DEFAULT_ANCHORS[label].low;
  const effectiveHigh = high || DEFAULT_ANCHORS[label].high;

  return `
    <div class="grid-note">Grid question — each attribute is rated on the scale below.</div>
    ${renderAnchorRow(effectiveLow, effectiveHigh)}
    ${renderScaleCircles(pts)}
  `;
}

function renderSemanticDifferential(
  options: ScaleOption[],
  anchors: Record<string, string> | undefined,
  attrPairs?: Array<{ left: string; right: string }>,
): string {
  const pts = options.length > 0 ? options : defaultScale(5);
  const circles = pts.map((o) => `<div class="sd-circle">${esc(String(o.value))}</div>`).join("");

  let rows: Array<{ left: string; right: string }> = [];
  if (attrPairs && attrPairs.length > 0) {
    rows = attrPairs;
  } else if (anchors) {
    const keys = Object.keys(anchors).sort();
    const left = anchors.low || (keys.length > 0 ? anchors[keys[0]] : "") || "";
    const right = anchors.high || (keys.length > 1 ? anchors[keys[keys.length - 1]] : "") || "";
    if (left || right) rows = [{ left, right }];
  }

  if (rows.length === 0) {
    return `
      <div class="grid-note">Semantic differential — each row shows a bipolar adjective pair rated on the scale below.</div>
      <div class="semantic-diff">
        <span class="sd-anchor-left">&lsaquo; Left anchor &rsaquo;</span>
        <div class="sd-points">${circles}</div>
        <span class="sd-anchor-right">&lsaquo; Right anchor &rsaquo;</span>
      </div>
    `;
  }

  return rows
    .map(
      (r) => `
      <div class="semantic-diff">
        <span class="sd-anchor-left">${esc(r.left)}</span>
        <div class="sd-points">${circles}</div>
        <span class="sd-anchor-right">${esc(r.right)}</span>
      </div>
    `,
    )
    .join("");
}

function renderRankingList(options: ScaleOption[]): string {
  if (options.length === 0) return '<div class="no-scale">No items to rank</div>';
  return `<div class="ranking-list">${options
    .map((o, i) => `<div class="ranking-item"><span class="rank-num">${i + 1}.</span> ${esc(o.label)}</div>`)
    .join("")}</div>`;
}

// ── Concept board HTML ───────────────────────────────────────────────

function renderConceptBoard(concept: ConceptResponse, index: number): string {
  const rows = COMPONENT_KEYS.map((key) => {
    const comp = (concept.components as Record<string, unknown>)[key] as Record<string, unknown> | undefined;
    if (!comp) return "";
    const text = getConceptDisplayText(comp);
    if (!text) return "";
    return `<tr><td class="comp-label">${esc(formatLabel(key))}</td><td class="comp-value">${esc(text)}</td></tr>`;
  }).join("");

  const image = concept.image_url
    ? `<div class="concept-image"><img src="${esc(concept.image_url)}" alt="Concept ${index + 1}" /></div>`
    : "";

  return `
    <div class="concept-board">
      <div class="concept-title">CONCEPT ${index + 1}</div>
      ${image}
      <table class="concept-table">${rows}</table>
    </div>
  `;
}

// ── Section HTML ─────────────────────────────────────────────────────

function renderSectionHeader(section: QuestionnaireSection): string {
  return `
    <div class="section-header">
      <div class="section-name">${esc(section.section_name)}</div>
      <div class="section-id">${esc(section.section_id)}</div>
      ${section.section_notes ? `<div class="section-notes">${esc(section.section_notes)}</div>` : ""}
    </div>
  `;
}

// ── Main export ──────────────────────────────────────────────────────

export function openPrintableSurvey(
  content: QuestionnaireContent,
  concepts: ConceptResponse[],
  studyTitle?: string,
): void {
  const sections = content.sections || [];

  // Partition sections using the same heuristic as QuestionnaireView
  const preConcept: QuestionnaireSection[] = [];
  const perConcept: QuestionnaireSection[] = [];
  const postConcept: QuestionnaireSection[] = [];

  for (const section of sections) {
    if (PRE_CONCEPT_IDS.has(section.section_id)) {
      preConcept.push(section);
    } else if (POST_CONCEPT_IDS.has(section.section_id)) {
      postConcept.push(section);
    } else if (isConceptSpecificSection(section)) {
      perConcept.push(section);
    } else {
      postConcept.push(section);
    }
  }

  let globalQ = 1;
  let body = "";

  // Title
  body += `
    <div class="title-block">
      <h1>${esc(studyTitle || "Survey Questionnaire")}</h1>
      <div class="meta">
        Version ${content.version} &middot;
        ${content.total_questions} questions &middot;
        ~${content.estimated_duration_minutes} minutes
      </div>
    </div>
  `;

  // Pre-concept sections
  for (const section of preConcept) {
    body += renderSectionHeader(section);
    for (const q of section.questions) {
      body += renderQuestionHeader(q, globalQ++);
    }
  }

  // Per-concept blocks: for each concept, show concept board, then all per-concept section questions
  if (perConcept.length > 0 && concepts.length > 0) {
    for (let ci = 0; ci < concepts.length; ci++) {
      body += `<div class="concept-block-divider">CONCEPT ${ci + 1} OF ${concepts.length}</div>`;
      body += renderConceptBoard(concepts[ci], ci);

      for (const section of perConcept) {
        const questionsToRender = section.questions.filter((q) => q.question_type !== "concept_exposure");
        if (questionsToRender.length === 0) continue;
        body += renderSectionHeader(section);
        for (const q of questionsToRender) {
          body += renderQuestionHeader(q, globalQ++);
        }
      }
    }
  } else if (perConcept.length > 0) {
    body += `<div class="concept-block-divider">CONCEPT EVALUATION (repeated per concept)</div>`;
    for (const section of perConcept) {
      body += renderSectionHeader(section);
      for (const q of section.questions) {
        body += renderQuestionHeader(q, globalQ++);
      }
    }
  }

  // Post-concept sections
  for (const section of postConcept) {
    body += renderSectionHeader(section);
    for (const q of section.questions) {
      body += renderQuestionHeader(q, globalQ++);
    }
  }

  // Open window
  const win = window.open("", "_blank");
  if (!win) {
    alert("Pop-up blocked. Please allow pop-ups for this site.");
    return;
  }

  win.document.write(`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Survey Preview — ${esc(studyTitle || "Questionnaire")}</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #1a1a1a; background: #fff;
    padding: 40px 48px; max-width: 820px; margin: 0 auto;
    line-height: 1.5; font-size: 13px;
  }
  .title-block { text-align: center; margin-bottom: 36px; padding-bottom: 20px; border-bottom: 2px solid #111; }
  .title-block h1 { font-size: 22px; font-weight: 700; margin-bottom: 6px; }
  .meta { font-size: 12px; color: #666; }
  .section-header { margin-top: 32px; margin-bottom: 16px; padding: 10px 14px; background: #f5f5f5; border-left: 4px solid #333; }
  .section-name { font-size: 15px; font-weight: 700; }
  .section-id { font-size: 10px; color: #999; font-family: monospace; margin-top: 2px; }
  .section-notes { font-size: 11px; color: #666; margin-top: 4px; font-style: italic; }
  .question { margin-bottom: 22px; padding: 14px 16px; border: 1px solid #ddd; border-radius: 6px; page-break-inside: avoid; }
  .q-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
  .q-num { font-weight: 700; font-size: 12px; color: #555; font-family: monospace; }
  .q-text { font-size: 14px; font-weight: 500; margin-bottom: 8px; line-height: 1.5; }
  .required { color: #e53e3e; font-weight: 700; }
  .type-badge, .scale-badge { display: inline-block; font-size: 10px; padding: 1px 6px; border-radius: 3px; font-weight: 600; }
  .type-badge { background: #eee; color: #555; }
  .scale-badge { background: #e0f2fe; color: #0369a1; }
  .design-notes { font-size: 10px; color: #888; font-style: italic; margin-bottom: 6px; }
  .show-if { font-size: 10px; color: #a855f7; margin-bottom: 4px; }
  .options-list { margin-top: 6px; }
  .option { display: flex; align-items: center; gap: 8px; padding: 5px 0; font-size: 13px; color: #333; }
  .radio-circle { display: inline-block; width: 14px; height: 14px; border: 1.5px solid #888; border-radius: 50%; flex-shrink: 0; }
  .checkbox-square { display: inline-block; width: 14px; height: 14px; border: 1.5px solid #888; border-radius: 2px; flex-shrink: 0; }
  .open-text-box { margin-top: 6px; border: 1px dashed #bbb; border-radius: 4px; height: 64px; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 12px; font-style: italic; }
  .anchor-row { display: flex; justify-content: space-between; font-size: 11px; color: #666; margin-bottom: 4px; }
  .rating-scale { display: flex; gap: 6px; align-items: flex-start; flex-wrap: wrap; margin-top: 4px; }
  .scale-point { display: flex; flex-direction: column; align-items: center; gap: 3px; }
  .scale-circle { width: 34px; height: 34px; border: 1.5px solid #888; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; color: #555; font-family: monospace; }
  .scale-label { font-size: 9px; color: #777; text-align: center; max-width: 64px; line-height: 1.2; }
  .grid-note { font-size: 11px; color: #888; font-style: italic; margin-bottom: 6px; }
  .semantic-diff { display: flex; align-items: center; gap: 10px; margin-top: 6px; margin-bottom: 6px; }
  .sd-anchor-left, .sd-anchor-right { font-size: 12px; font-weight: 600; color: #444; white-space: nowrap; min-width: 80px; }
  .sd-anchor-left { text-align: right; }
  .sd-anchor-right { text-align: left; }
  .sd-points { display: flex; gap: 4px; }
  .sd-circle { width: 30px; height: 30px; border: 1.5px solid #888; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #666; font-family: monospace; }
  .ranking-list { margin-top: 6px; }
  .ranking-item { padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 4px; font-size: 13px; color: #333; }
  .rank-num { font-weight: 700; color: #888; font-family: monospace; margin-right: 4px; }
  .no-scale { font-size: 11px; color: #aaa; font-style: italic; margin-top: 4px; }
  .concept-placeholder { font-size: 11px; color: #aaa; font-style: italic; padding: 8px; background: #fafafa; border-radius: 4px; margin-top: 4px; }
  .concept-block-divider {
    margin-top: 40px; margin-bottom: 16px; padding: 10px 0;
    text-align: center; font-size: 14px; font-weight: 700; letter-spacing: 1px;
    color: #fff; background: #333; border-radius: 4px;
    page-break-before: always;
  }
  .concept-block-divider:first-of-type { page-break-before: auto; }
  .concept-board { border: 2px solid #333; border-radius: 8px; padding: 20px; margin-bottom: 20px; page-break-inside: avoid; background: #fafafa; }
  .concept-title { font-size: 16px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; text-align: center; }
  .concept-image { text-align: center; margin-bottom: 12px; }
  .concept-image img { max-width: 100%; max-height: 200px; object-fit: contain; border-radius: 4px; }
  .concept-table { width: 100%; border-collapse: collapse; }
  .concept-table tr { border-bottom: 1px solid #e5e5e5; }
  .concept-table tr:last-child { border-bottom: none; }
  .comp-label { font-size: 11px; font-weight: 700; color: #666; padding: 8px 10px 8px 0; width: 140px; vertical-align: top; text-transform: uppercase; letter-spacing: 0.5px; }
  .comp-value { font-size: 13px; color: #222; padding: 8px 0; line-height: 1.5; }
  @media print {
    body { padding: 20px 24px; font-size: 11px; }
    .question { break-inside: avoid; }
    .concept-board { break-inside: avoid; }
    .no-print { display: none !important; }
  }
  .print-bar { position: fixed; top: 0; left: 0; right: 0; background: #111; color: #fff; padding: 10px 20px; display: flex; align-items: center; justify-content: space-between; z-index: 9999; }
  .print-bar button { padding: 6px 20px; background: #22c55e; color: #000; border: none; border-radius: 4px; font-weight: 700; font-size: 13px; cursor: pointer; }
  .print-bar button:hover { background: #16a34a; }
  body { padding-top: 60px; }
  @media print { .print-bar { display: none; } body { padding-top: 0; } }
</style>
</head>
<body>
  <div class="print-bar no-print">
    <span>Survey Preview</span>
    <button onclick="window.print()">Save as PDF / Print</button>
  </div>
  ${body}
</body>
</html>`);

  win.document.close();
}
