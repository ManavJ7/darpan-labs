/**
 * Tests for printSurvey.ts — validates the HTML generation logic.
 * Since openPrintableSurvey opens a browser window, we test the internal
 * rendering by importing the module and verifying the generated HTML
 * indirectly through a mock window.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import type {
  QuestionnaireContent,
  QuestionnaireSection,
  Question,
  ConceptResponse,
} from "@/types/study";

// ── Fixtures ─────────────────────────────────────────────────────────

function makeQuestion(overrides: Partial<Question> = {}): Question {
  return {
    question_id: "Q1",
    section: "S1_screening",
    question_text: { en: "Test question?" },
    question_type: "single_select",
    randomize: false,
    required: true,
    position_in_section: 1,
    ...overrides,
  };
}

function makeSection(id: string, name: string, questions: Question[]): QuestionnaireSection {
  return { section_id: id, section_name: name, questions };
}

function makeContent(sections: QuestionnaireSection[]): QuestionnaireContent {
  return {
    questionnaire_id: "QNR-test",
    study_id: "study-1",
    version: 1,
    estimated_duration_minutes: 15,
    total_questions: sections.reduce((n, s) => n + s.questions.length, 0),
    sections,
    quality_controls: {
      attention_check: {},
      speeder_threshold_seconds: 120,
      straightline_detection: true,
      open_end_quality_check: true,
    },
    survey_logic: {
      concept_rotation: "random",
      concepts_per_respondent: 2,
      randomize_within_section: [],
      skip_logic: [],
    },
  } as QuestionnaireContent;
}

function makeConcept(id: string): ConceptResponse {
  return {
    id,
    study_id: "study-1",
    concept_number: 1,
    components: {
      product_name: { raw_input: `Product ${id}` },
    },
    status: "draft",
    created_at: "2026-01-01T00:00:00Z",
  } as ConceptResponse;
}

// ── Mock window.open ─────────────────────────────────────────────────

let capturedHTML = "";

beforeEach(() => {
  capturedHTML = "";
  const mockWin = {
    document: {
      write: (html: string) => {
        capturedHTML += html;
      },
      close: vi.fn(),
    },
  };
  vi.spyOn(window, "open").mockReturnValue(mockWin as unknown as Window);
});

// ── Tests ────────────────────────────────────────────────────────────

describe("printSurvey — HTML generation", () => {
  it("renders title and metadata", async () => {
    const { openPrintableSurvey } = await import("@/components/steps/printSurvey");
    const content = makeContent([]);
    openPrintableSurvey(content, [], "My Study");

    expect(capturedHTML).toContain("My Study");
    expect(capturedHTML).toContain("Version 1");
    expect(capturedHTML).toContain("15 minutes");
  });

  it("renders single_select options as radio buttons", async () => {
    const { openPrintableSurvey } = await import("@/components/steps/printSurvey");
    const q = makeQuestion({
      question_type: "single_select",
      scale: {
        type: "categorical",
        options: [
          { value: 1, label: "Yes" },
          { value: 2, label: "No" },
        ],
      },
    });
    const content = makeContent([makeSection("S1_screening", "Screening", [q])]);
    openPrintableSurvey(content, []);

    expect(capturedHTML).toContain("radio-circle");
    expect(capturedHTML).toContain("Yes");
    expect(capturedHTML).toContain("No");
  });

  it("renders open_text as text box", async () => {
    const { openPrintableSurvey } = await import("@/components/steps/printSurvey");
    const q = makeQuestion({ question_type: "open_text" });
    const content = makeContent([makeSection("S1_screening", "Screening", [q])]);
    openPrintableSurvey(content, []);

    expect(capturedHTML).toContain("open-text-box");
  });

  it("generates default 5-point scale for rating with empty options", async () => {
    const { openPrintableSurvey } = await import("@/components/steps/printSurvey");
    const q = makeQuestion({
      question_type: "rating",
      scale: { type: "categorical", options: [] },
    });
    const content = makeContent([makeSection("S1_screening", "Screening", [q])]);
    openPrintableSurvey(content, []);

    // Should have scale circles, not "Scale options not specified"
    expect(capturedHTML).toContain("scale-circle");
    expect(capturedHTML).not.toContain("not specified");
  });

  it("renders likert with default labels when options are empty", async () => {
    const { openPrintableSurvey } = await import("@/components/steps/printSurvey");
    const q = makeQuestion({
      question_type: "rating",
      scale: { type: "likert_5pt", options: [] },
    });
    const content = makeContent([makeSection("S1_screening", "Screening", [q])]);
    openPrintableSurvey(content, []);

    expect(capturedHTML).toContain("Strongly disagree");
    expect(capturedHTML).toContain("Strongly agree");
  });

  it("renders importance with default anchors when empty", async () => {
    const { openPrintableSurvey } = await import("@/components/steps/printSurvey");
    const q = makeQuestion({
      question_type: "rating",
      scale: { type: "importance", options: [] },
    });
    const content = makeContent([makeSection("S5_diagnostic", "Diagnostic", [q])]);
    openPrintableSurvey(content, []);

    expect(capturedHTML).toContain("Not at all important");
    expect(capturedHTML).toContain("Extremely important");
    expect(capturedHTML).toContain("Grid question");
  });

  it("renders performance with default anchors when empty", async () => {
    const { openPrintableSurvey } = await import("@/components/steps/printSurvey");
    const q = makeQuestion({
      question_type: "rating",
      scale: { type: "performance", options: [] },
    });
    const content = makeContent([makeSection("S5_diagnostic", "Diagnostic", [q])]);
    openPrintableSurvey(content, []);

    expect(capturedHTML).toContain("Very poor");
    expect(capturedHTML).toContain("Excellent");
  });

  it("renders semantic_differential placeholder when no anchors/pairs", async () => {
    const { openPrintableSurvey } = await import("@/components/steps/printSurvey");
    const q = makeQuestion({
      question_type: "rating",
      scale: { type: "semantic_differential", options: [] },
    });
    const content = makeContent([makeSection("S5_diagnostic", "Diagnostic", [q])]);
    openPrintableSurvey(content, []);

    expect(capturedHTML).toContain("Semantic differential");
    expect(capturedHTML).toContain("sd-circle"); // scale points shown
  });

  it("renders semantic_differential with attribute_pairs", async () => {
    const { openPrintableSurvey } = await import("@/components/steps/printSurvey");
    const q = makeQuestion({
      question_type: "rating",
      scale: {
        type: "semantic_differential",
        options: [],
        attribute_pairs: [
          { left: "Boring", right: "Exciting" },
        ],
      } as unknown as Question["scale"],
    });
    const content = makeContent([makeSection("S5_diagnostic", "Diagnostic", [q])]);
    openPrintableSurvey(content, []);

    expect(capturedHTML).toContain("Boring");
    expect(capturedHTML).toContain("Exciting");
  });

  it("interleaves per-concept sections with concept boards", async () => {
    const { openPrintableSurvey } = await import("@/components/steps/printSurvey");
    // S3 has a concept_exposure question → per-concept
    const q1 = makeQuestion({
      question_type: "concept_exposure",
      question_text: { en: "Please review this concept" },
    });
    const q2 = makeQuestion({
      question_id: "Q2",
      question_type: "rating",
      question_text: { en: "How likely are you to buy this product?" },
      scale: { type: "behavioral", options: [{ value: 1, label: "Definitely" }] },
    });
    const content = makeContent([
      makeSection("S1_screening", "Screening", []),
      makeSection("S3_concept_exposure", "Concept Exposure", [q1]),
      makeSection("S4_core_kpi", "KPI", [q2]),
      makeSection("S8_demographics", "Demographics", []),
    ]);
    const concepts = [makeConcept("c1"), makeConcept("c2")];
    openPrintableSurvey(content, concepts);

    // Should have concept dividers for both concepts
    expect(capturedHTML).toContain("CONCEPT 1 OF 2");
    expect(capturedHTML).toContain("CONCEPT 2 OF 2");
    // Concept boards rendered
    expect(capturedHTML).toContain("Product c1");
    expect(capturedHTML).toContain("Product c2");
  });

  it("classifies price_sensitivity as per-concept when it references 'this product'", async () => {
    const { openPrintableSurvey } = await import("@/components/steps/printSurvey");
    const exposure = makeQuestion({
      question_type: "concept_exposure",
      question_text: { en: "Review this concept" },
    });
    const priceQ = makeQuestion({
      question_id: "Q_price",
      question_type: "single_select",
      question_text: { en: "How likely would you buy this product at the shown price?" },
      scale: {
        type: "behavioral",
        options: [{ value: 1, label: "Definitely" }],
      },
    });
    const content = makeContent([
      makeSection("S3_concept_exposure", "Exposure", [exposure]),
      makeSection("S7_price_sensitivity", "Price", [priceQ]),
      makeSection("S8_demographics", "Demographics", []),
    ]);
    const concepts = [makeConcept("c1")];
    openPrintableSurvey(content, concepts);

    // Price section should be inside the concept block (before demographics)
    const conceptDividerIdx = capturedHTML.indexOf("CONCEPT 1 OF 1");
    const priceIdx = capturedHTML.indexOf("this product at the shown price");
    const demoIdx = capturedHTML.indexOf("Demographics");
    // Price appears after concept divider but before demographics
    expect(conceptDividerIdx).toBeLessThan(priceIdx);
    expect(priceIdx).toBeLessThan(demoIdx);
  });
});
