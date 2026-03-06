import uuid
from datetime import datetime
from typing import Optional

from app.schemas.common import BaseSchema


class ConceptComponent(BaseSchema):
    raw_input: str
    refined: Optional[str] = None
    refinement_rationale: Optional[str] = None
    approved: bool = False
    brand_edit: Optional[str] = None


class ConceptComponents(BaseSchema):
    consumer_insight: ConceptComponent
    product_name: ConceptComponent
    key_benefit: ConceptComponent
    reasons_to_believe: ConceptComponent
    visual: dict
    price_format: dict


class ConceptCreate(BaseSchema):
    components: ConceptComponents


class ConceptResponse(BaseSchema):
    id: uuid.UUID
    study_id: uuid.UUID
    concept_index: int
    version: int
    status: str
    components: dict
    comparability_flags: Optional[list] = None
    image_url: Optional[str] = None
    created_at: datetime


class ConceptRefineResponse(BaseSchema):
    concept_id: uuid.UUID
    refined_components: dict
    flags: list[str] = []
    testability_score: float


class ComparabilityCheckResponse(BaseSchema):
    overall_comparability: str  # pass | warning | fail
    issues: list[str] = []
    recommendation: str
