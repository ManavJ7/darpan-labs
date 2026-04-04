"""Interview-related Pydantic schemas."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from .common import BaseSchema


class SensitivitySettings(BaseModel):
    """Sensitivity settings for interview."""

    allow_sensitive_topics: bool = False
    allowed_sensitive_categories: list[str] = Field(default_factory=list)


class ConsentData(BaseModel):
    """Consent information for interview."""

    accepted: bool
    consent_version: str = "v2.0"
    allow_audio_storage_days: int = 7
    allow_data_retention_days: int = 30


class OptionItemSchema(BaseModel):
    """Option for select/rank/matrix questions."""

    label: str
    value: str


class ConceptCardSchema(BaseModel):
    """Structured concept card for concept test display."""

    concept_id: str
    name: str
    consumer_insight: str
    key_benefit: str
    how_it_works: str
    packaging: str
    price: str


class InterviewStartRequest(BaseModel):
    """Request to start an interview session."""

    user_id: UUID
    input_mode: Literal["voice", "text"] = "text"
    language_preference: Literal["auto", "en", "hi"] = "auto"
    modules_to_complete: list[str] = Field(
        default=["M1", "M2", "M3", "M4", "M5", "M6", "M7"],
        description="Module IDs to complete in this session",
    )
    sensitivity_settings: SensitivitySettings = Field(
        default_factory=SensitivitySettings
    )
    consent: ConsentData | None = None


class QuestionMeta(BaseModel):
    """Metadata for a question."""

    question_id: str
    question_type: str
    target_signal: str
    rationale: str | None = None
    is_followup: bool = False
    parent_question_id: str | None = None
    # Rich UI fields
    options: list[OptionItemSchema] | None = None
    max_selections: int | None = None
    scale_min: int | None = None
    scale_max: int | None = None
    scale_labels: dict[str, str] | None = None
    matrix_items: list[str] | None = None
    matrix_options: list[OptionItemSchema] | None = None
    placeholder: str | None = None
    concept_card: ConceptCardSchema | None = None


class ModuleInfo(BaseModel):
    """Information about a module."""

    module_id: str
    module_name: str
    estimated_duration_min: int
    total_questions: int = 0
    status: Literal["pending", "active", "completed", "skipped"] = "pending"


class FirstQuestion(BaseModel):
    """First question to ask."""

    question_id: str
    question_text: str
    question_type: str
    target_signal: str
    # Rich UI fields
    options: list[OptionItemSchema] | None = None
    max_selections: int | None = None
    scale_min: int | None = None
    scale_max: int | None = None
    scale_labels: dict[str, str] | None = None
    matrix_items: list[str] | None = None
    matrix_options: list[OptionItemSchema] | None = None
    placeholder: str | None = None
    concept_card: ConceptCardSchema | None = None


class ModulePlanItem(BaseModel):
    """Module plan item."""

    module_id: str
    status: Literal["pending", "active", "completed", "skipped"]
    est_min: int


class VoiceConfig(BaseModel):
    """Voice configuration for interview."""

    websocket_url: str | None = None
    audio_format: str = "pcm_16khz_mono"
    tts_voice: str = "en-IN-neural-female"
    vad_config: dict = Field(
        default_factory=lambda: {
            "silence_threshold_ms": 1500,
            "min_speech_duration_ms": 300,
        }
    )


class InterviewStartResponse(BaseSchema):
    """Response after starting an interview session."""

    session_id: UUID
    status: str
    voice_config: VoiceConfig | None = None
    first_module: ModuleInfo
    module_plan: list[ModulePlanItem]
    first_question: FirstQuestion


class InterviewAnswerRequest(BaseModel):
    """Request to submit an answer."""

    answer_text: str
    question_id: str
    input_mode: Literal["voice", "text"] = "text"
    audio_meta: dict | None = None


class InterviewAnswerResponse(BaseSchema):
    """Response after submitting an answer."""

    turn_id: UUID
    answer_received: bool = True
    answer_meta: dict | None = None


class ModuleProgress(BaseModel):
    """Progress within a module."""

    module_id: str
    module_name: str
    questions_asked: int
    total_questions: int
    coverage_score: float
    confidence_score: float
    signals_captured: list[str]
    status: Literal["pending", "active", "completed", "skipped"]


class InterviewNextQuestionResponse(BaseSchema):
    """Response with next question."""

    question_id: str | None = None
    question_text: str | None = None
    question_type: str | None = None
    question_meta: QuestionMeta | None = None
    module_id: str
    module_progress: ModuleProgress
    status: Literal["continue", "module_complete", "all_modules_complete"]
    module_summary: str | None = None
    acknowledgment_text: str | None = None
    # Rich UI fields (top-level for convenience)
    options: list[OptionItemSchema] | None = None
    max_selections: int | None = None
    scale_min: int | None = None
    scale_max: int | None = None
    scale_labels: dict[str, str] | None = None
    matrix_items: list[str] | None = None
    matrix_options: list[OptionItemSchema] | None = None
    placeholder: str | None = None
    concept_card: ConceptCardSchema | None = None


class InterviewStatusResponse(BaseSchema):
    """Full interview session status."""

    session_id: UUID
    status: Literal["active", "completed", "paused"]
    input_mode: str
    language_preference: str
    started_at: datetime
    total_duration_sec: int | None
    modules: list[ModuleProgress]
    current_module: str | None
    completed_modules: list[str]


class InterviewSkipRequest(BaseModel):
    """Request to skip a question."""

    reason: str | None = None


class InterviewPauseResponse(BaseSchema):
    """Response after pausing interview."""

    session_id: UUID
    status: str = "paused"
    can_resume: bool = True
    resume_at_module: str
    resume_at_question: int


class UserModuleStatus(BaseModel):
    """Status of a single module for a user."""

    module_id: str
    module_name: str
    description: str
    status: Literal["not_started", "in_progress", "completed"]
    coverage_score: float | None = None
    confidence_score: float | None = None
    estimated_duration_min: int = 3
    session_id: UUID | None = None  # Session where this module was completed


class UserModulesResponse(BaseSchema):
    """Response with all modules and their completion status for a user."""

    user_id: UUID
    modules: list[UserModuleStatus]
    completed_count: int
    total_required: int = 7
    can_generate_twin: bool


class StartSingleModuleRequest(BaseModel):
    """Request to start a specific module."""

    user_id: UUID
    module_id: str
    input_mode: Literal["voice", "text"] = "text"
    language_preference: Literal["auto", "en", "hi"] = "auto"
    consent: ConsentData | None = None


class ModuleCompleteResponse(BaseSchema):
    """Response when a single module is completed."""

    session_id: UUID
    module_id: str
    module_name: str
    status: str = "module_completed"
    module_summary: str | None = None
    coverage_score: float
    confidence_score: float
    can_generate_twin: bool
    remaining_modules: list[str]


