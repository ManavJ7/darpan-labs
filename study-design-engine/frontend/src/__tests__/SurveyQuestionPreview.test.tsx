import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SurveyQuestionPreview } from "@/components/steps/SurveyQuestionPreview";
import type { Question, ConceptResponse } from "@/types/study";

// ── Test Fixtures ────────────────────────────────────────────────────

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

function makeConcept(overrides: Partial<ConceptResponse> = {}): ConceptResponse {
  return {
    id: "c1",
    study_id: "s1",
    concept_number: 1,
    components: {
      product_name: { raw_input: "Test Product" },
      key_benefit: { refined: "Great benefit" },
    },
    status: "draft",
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  } as ConceptResponse;
}

const NO_CONCEPTS: ConceptResponse[] = [];

// ── Header / Metadata ────────────────────────────────────────────────

describe("SurveyQuestionPreview — header", () => {
  it("renders question text", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({ question_text: { en: "How old are you?" } })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText("How old are you?")).toBeInTheDocument();
  });

  it("renders position number", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({ position_in_section: 3 })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText("Q3")).toBeInTheDocument();
  });

  it("shows Required badge when required=true", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({ required: true })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText("Required")).toBeInTheDocument();
  });

  it("hides Required badge when required=false", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({ required: false })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.queryByText("Required")).not.toBeInTheDocument();
  });

  it("shows scale type badge when scale.type is set", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({
          question_type: "rating",
          scale: { type: "likert_5pt", options: [] },
        })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText("likert_5pt")).toBeInTheDocument();
  });

  it("shows design notes", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({ design_notes: "Use 5-point scale" })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText("Use 5-point scale")).toBeInTheDocument();
  });

  it("shows show_if condition", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({ show_if: "Q1 == 1" })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText(/Show if: Q1 == 1/)).toBeInTheDocument();
  });
});

// ── Single Select ────────────────────────────────────────────────────

describe("SurveyQuestionPreview — single_select", () => {
  it("renders radio options", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({
          question_type: "single_select",
          scale: {
            type: "categorical",
            options: [
              { value: 1, label: "Yes" },
              { value: 2, label: "No" },
            ],
          },
        })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText("Yes")).toBeInTheDocument();
    expect(screen.getByText("No")).toBeInTheDocument();
  });

  it("shows empty notice when no options", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({
          question_type: "single_select",
          scale: { type: "categorical", options: [] },
        })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText(/No options defined/)).toBeInTheDocument();
  });
});

// ── Multi Select ─────────────────────────────────────────────────────

describe("SurveyQuestionPreview — multi_select", () => {
  it("renders checkbox options", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({
          question_type: "multi_select",
          scale: {
            type: "categorical",
            options: [
              { value: 1, label: "A" },
              { value: 2, label: "B" },
              { value: 3, label: "C" },
            ],
          },
        })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    expect(screen.getByText("C")).toBeInTheDocument();
  });
});

// ── Open Text ────────────────────────────────────────────────────────

describe("SurveyQuestionPreview — open_text", () => {
  it("renders a disabled textarea", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({ question_type: "open_text" })}
        concepts={NO_CONCEPTS}
      />,
    );
    const textarea = screen.getByPlaceholderText(/Respondent types/);
    expect(textarea).toBeInTheDocument();
    expect(textarea).toBeDisabled();
  });
});

// ── Rating — Generic ─────────────────────────────────────────────────

describe("SurveyQuestionPreview — rating (generic)", () => {
  it("renders provided options as scale circles", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({
          question_type: "rating",
          scale: {
            type: "categorical",
            options: [
              { value: 1, label: "Bad" },
              { value: 2, label: "OK" },
              { value: 3, label: "Good" },
            ],
          },
        })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText("Bad")).toBeInTheDocument();
    expect(screen.getByText("OK")).toBeInTheDocument();
    expect(screen.getByText("Good")).toBeInTheDocument();
  });

  it("generates default 5-point scale when options are empty", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({
          question_type: "rating",
          scale: { type: "categorical", options: [] },
        })}
        concepts={NO_CONCEPTS}
      />,
    );
    // Should render 5 scale points, not "Scale options not available"
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.queryByText(/not available/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/not specified/i)).not.toBeInTheDocument();
  });

  it("renders anchors when provided", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({
          question_type: "rating",
          scale: {
            type: "categorical",
            options: [
              { value: 1, label: "1" },
              { value: 2, label: "2" },
              { value: 3, label: "3" },
            ],
            anchors: { low: "Poor", high: "Excellent" },
          },
        })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText("Poor")).toBeInTheDocument();
    expect(screen.getByText("Excellent")).toBeInTheDocument();
  });
});

// ── Rating — Likert ──────────────────────────────────────────────────

describe("SurveyQuestionPreview — rating (likert)", () => {
  it("generates labeled Likert defaults when options are empty", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({
          question_type: "rating",
          scale: { type: "likert_5pt", options: [] },
        })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText("Strongly disagree")).toBeInTheDocument();
    expect(screen.getByText("Neutral")).toBeInTheDocument();
    expect(screen.getByText("Strongly agree")).toBeInTheDocument();
  });
});

// ── Rating — Importance ──────────────────────────────────────────────

describe("SurveyQuestionPreview — rating (importance)", () => {
  it("shows grid note and default anchors when options are empty", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({
          question_type: "rating",
          scale: { type: "importance", options: [], anchors: undefined },
        })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText(/Grid question/)).toBeInTheDocument();
    expect(screen.getByText("Not at all important")).toBeInTheDocument();
    expect(screen.getByText("Extremely important")).toBeInTheDocument();
    // Should still render 5-point scale
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });
});

// ── Rating — Performance ─────────────────────────────────────────────

describe("SurveyQuestionPreview — rating (performance)", () => {
  it("shows grid note and default anchors when options are empty", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({
          question_type: "rating",
          scale: { type: "performance", options: [], anchors: undefined },
        })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText(/Grid question/)).toBeInTheDocument();
    expect(screen.getByText("Very poor")).toBeInTheDocument();
    expect(screen.getByText("Excellent")).toBeInTheDocument();
  });
});

// ── Rating — Semantic Differential ───────────────────────────────────

describe("SurveyQuestionPreview — rating (semantic_differential)", () => {
  it("renders attribute pairs when provided", () => {
    const scale = {
      type: "semantic_differential",
      options: [
        { value: 1, label: "1" },
        { value: 2, label: "2" },
        { value: 3, label: "3" },
        { value: 4, label: "4" },
        { value: 5, label: "5" },
      ],
      attribute_pairs: [
        { left: "Boring", right: "Exciting" },
        { left: "Low Quality", right: "High Quality" },
      ],
    };
    render(
      <SurveyQuestionPreview
        question={makeQuestion({
          question_type: "rating",
          scale: scale as unknown as Question["scale"],
        })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText("Boring")).toBeInTheDocument();
    expect(screen.getByText("Exciting")).toBeInTheDocument();
    expect(screen.getByText("Low Quality")).toBeInTheDocument();
    expect(screen.getByText("High Quality")).toBeInTheDocument();
  });

  it("renders anchor pair when attribute_pairs is missing but anchors exist", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({
          question_type: "rating",
          scale: {
            type: "semantic_differential",
            options: [],
            anchors: { low: "Cold", high: "Warm" },
          },
        })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText("Cold")).toBeInTheDocument();
    expect(screen.getByText("Warm")).toBeInTheDocument();
  });

  it("shows placeholder when both anchors and attribute_pairs are missing", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({
          question_type: "rating",
          scale: {
            type: "semantic_differential",
            options: [],
            anchors: undefined,
          },
        })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText(/Semantic differential/)).toBeInTheDocument();
    // Should still render scale points, not "Scale options not available"
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });
});

// ── Ranking ──────────────────────────────────────────────────────────

describe("SurveyQuestionPreview — ranking", () => {
  it("renders numbered items", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({
          question_type: "ranking",
          scale: {
            type: "ranking",
            options: [
              { value: 1, label: "Price" },
              { value: 2, label: "Quality" },
              { value: 3, label: "Brand" },
            ],
          },
        })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText("Price")).toBeInTheDocument();
    expect(screen.getByText("Quality")).toBeInTheDocument();
    expect(screen.getByText("Brand")).toBeInTheDocument();
    expect(screen.getByText("1.")).toBeInTheDocument();
    expect(screen.getByText("3.")).toBeInTheDocument();
  });

  it("shows empty notice when no options", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({
          question_type: "ranking",
          scale: { type: "ranking", options: [] },
        })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText(/No items to rank/)).toBeInTheDocument();
  });
});

// ── Concept Exposure ─────────────────────────────────────────────────

describe("SurveyQuestionPreview — concept_exposure", () => {
  it("renders all concepts when no conceptIndex", () => {
    const concepts = [
      makeConcept({ id: "c1", concept_number: 1 }),
      makeConcept({ id: "c2", concept_number: 2 }),
    ];
    render(
      <SurveyQuestionPreview
        question={makeQuestion({ question_type: "concept_exposure" })}
        concepts={concepts}
      />,
    );
    expect(screen.getByText("Concept 1")).toBeInTheDocument();
    expect(screen.getByText("Concept 2")).toBeInTheDocument();
  });

  it("renders only the indexed concept when conceptIndex is set", () => {
    const concepts = [
      makeConcept({ id: "c1", concept_number: 1 }),
      makeConcept({ id: "c2", concept_number: 2 }),
    ];
    render(
      <SurveyQuestionPreview
        question={makeQuestion({ question_type: "concept_exposure" })}
        concepts={concepts}
        conceptIndex={1}
      />,
    );
    // Only concept at index 1 should render
    expect(screen.getByText("Concept 1")).toBeInTheDocument(); // Note: rendered as idx+1 in the array passed
    expect(screen.queryByText("Concept 2")).not.toBeInTheDocument();
  });

  it("shows loading state when concepts array is empty", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({ question_type: "concept_exposure" })}
        concepts={[]}
      />,
    );
    expect(screen.getByText(/Loading concepts/)).toBeInTheDocument();
  });

  it("renders concept component details", () => {
    const concepts = [
      makeConcept({
        components: {
          product_name: { raw_input: "SuperWidget" },
          key_benefit: { refined: "Saves time" },
        },
      }),
    ];
    render(
      <SurveyQuestionPreview
        question={makeQuestion({ question_type: "concept_exposure" })}
        concepts={concepts}
      />,
    );
    expect(screen.getByText("SuperWidget")).toBeInTheDocument();
    expect(screen.getByText("Saves time")).toBeInTheDocument();
  });
});

// ── Fallback ─────────────────────────────────────────────────────────

describe("SurveyQuestionPreview — unknown question type", () => {
  it("renders as radio list when options exist", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({
          question_type: "custom_type" as string,
          scale: {
            type: "categorical",
            options: [{ value: 1, label: "Option A" }],
          },
        })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByText("Option A")).toBeInTheDocument();
  });

  it("renders as text box when no options", () => {
    render(
      <SurveyQuestionPreview
        question={makeQuestion({ question_type: "custom_type" as string })}
        concepts={NO_CONCEPTS}
      />,
    );
    expect(screen.getByPlaceholderText(/Respondent types/)).toBeInTheDocument();
  });
});
