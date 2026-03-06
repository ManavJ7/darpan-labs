import uuid
from datetime import datetime
from typing import Optional

from app.schemas.common import BaseSchema


class SampleSizeParams(BaseSchema):
    methodology: str
    num_concepts: int
    concepts_per_respondent: int = 3
    confidence_level: float = 0.95
    margin_of_error: float = 0.05
    num_subgroups: int = 1
    min_per_subgroup: int = 30


class SampleSizeResult(BaseSchema):
    total_respondents: int
    per_concept: int
    incidence_adjusted: int
    recommended_panel_size: int


class QuotaAllocation(BaseSchema):
    dimension: str
    segments: list[dict]  # [{range, target_pct, target_n, min_n}]


class ResearchDesignContent(BaseSchema):
    testing_methodology: str
    concepts_per_respondent: int
    total_sample_size: int
    confidence_level: float
    margin_of_error: float
    demographic_quotas: list[dict]
    rotation_design: str
    data_collection_method: str
    survey_language: list[str] = ["english"]
    estimated_field_duration: Optional[int] = None
    estimated_cost: Optional[int] = None


class ResearchDesignResponse(BaseSchema):
    id: uuid.UUID
    study_id: uuid.UUID
    step: int
    version: int
    content: dict
    ai_rationale: Optional[dict] = None
    created_at: datetime
