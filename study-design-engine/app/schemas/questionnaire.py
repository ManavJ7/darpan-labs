from typing import Optional

from pydantic import field_validator

from app.schemas.common import BaseSchema


class QuestionScale(BaseSchema):
    type: str
    options: list[dict] = []  # [{value, label}]
    anchors: Optional[dict] = None  # Alternative format from LLM: {"1": "low", "5": "high"}

    @field_validator("options", mode="before")
    @classmethod
    def coerce_string_options(cls, v: list) -> list[dict]:
        """LLM sometimes returns plain strings instead of {value, label} dicts."""
        coerced = []
        for i, item in enumerate(v):
            if isinstance(item, str):
                coerced.append({"value": i + 1, "label": item})
            else:
                coerced.append(item)
        return coerced


class Question(BaseSchema):
    question_id: str
    section: str
    metric_id: Optional[str] = None
    question_text: dict  # {en: str, hi: str}
    question_type: str
    scale: Optional[QuestionScale] = None
    show_if: Optional[str] = None
    pipe_from: Optional[str] = None
    randomize: bool = False
    required: bool = True
    position_in_section: int
    design_notes: Optional[str] = None


class QuestionnaireSection(BaseSchema):
    section_id: str
    section_name: str
    questions: list[Question]
    section_notes: Optional[str] = None


class QualityControls(BaseSchema):
    attention_check: dict
    speeder_threshold_seconds: int
    straightline_detection: bool
    open_end_quality_check: bool


class SurveyLogic(BaseSchema):
    concept_rotation: str
    concepts_per_respondent: int
    randomize_within_section: list[str] = []
    skip_logic: list[dict] = []


class QuestionnaireContent(BaseSchema):
    questionnaire_id: str
    study_id: str
    version: int
    estimated_duration_minutes: int
    total_questions: int
    sections: list[QuestionnaireSection]
    quality_controls: QualityControls
    survey_logic: SurveyLogic


class SectionFeedbackRequest(BaseSchema):
    section_id: str
    feedback_text: str
    target_question_id: Optional[str] = None
    feedback_type: str  # specific_question | section_level | add_question | remove_question


class SectionFeedbackResponse(BaseSchema):
    updated_section: QuestionnaireSection
    change_log: list[str] = []
    warnings: list[str] = []
