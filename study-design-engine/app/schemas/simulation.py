import uuid
from datetime import datetime
from typing import Optional

from app.schemas.common import BaseSchema


# ─── Simulation Payload (served to bridge script) ─────────

class SimulationQuestion(BaseSchema):
    question_id: str
    question_text: dict  # {en: str, ...}
    question_type: str
    scale: Optional[dict] = None
    show_if: Optional[str] = None
    required: bool = True
    section: str
    position_in_section: int


class ConceptText(BaseSchema):
    concept_index: int
    # Concept-testing fields (product concepts)
    product_name: str = ""
    consumer_insight: str = ""
    key_benefit: str = ""
    reasons_to_believe: str = ""
    # Ad-creative-testing fields (creative territories)
    territory_name: Optional[str] = None
    core_insight: Optional[str] = None
    big_idea: Optional[str] = None
    key_message: Optional[str] = None
    execution_sketch: Optional[str] = None
    tone_mood: Optional[list[str]] = None
    target_emotion: Optional[list[str]] = None


class SimulationPayload(BaseSchema):
    study_id: str
    study_title: Optional[str] = None
    brand_name: Optional[str] = None
    category: Optional[str] = None
    questions: list[SimulationQuestion]
    concepts: list[ConceptText]
    # For ad_creative_testing: the locked Product Brief content. Used as Batch 0
    # shared context for twin simulation (written to ChromaDB so every batch
    # retrieves it during RAG).
    product_brief: Optional[dict] = None


# ─── Simulation Results (uploaded by bridge script) ───────

class TwinResponseItem(BaseSchema):
    question_id: str
    question_text: Optional[str] = None
    question_type: Optional[str] = None
    raw_answer: Optional[str] = None
    structured_answer: Optional[object] = None
    skipped: bool = False
    inference_mode: Optional[str] = None
    evidence_count: int = 0
    elapsed_s: float = 0.0


class TwinResult(BaseSchema):
    twin_id: str
    participant_id: Optional[str] = None
    coherence_score: Optional[float] = None
    responses: list[TwinResponseItem]


class SimulationResultUpload(BaseSchema):
    study_id: str
    study_title: Optional[str] = None
    simulation_date: Optional[str] = None
    inference_mode: str = "combined"
    twin_count: int = 0
    question_count: int = 0
    results: list[TwinResult]


class SimulationRunResponse(BaseSchema):
    id: uuid.UUID
    study_id: uuid.UUID
    status: str
    inference_mode: Optional[str] = None
    twin_count: Optional[int] = None
    question_count: Optional[int] = None
    results: dict
    summary: Optional[dict] = None
    created_at: datetime
