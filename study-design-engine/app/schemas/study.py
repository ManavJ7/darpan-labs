import uuid
from datetime import datetime
from typing import Optional

from app.schemas.common import BaseSchema


class StudyCreate(BaseSchema):
    question: str
    brand_id: uuid.UUID
    brand_name: Optional[str] = None
    category: Optional[str] = None
    context: Optional[dict] = None


class StudyResponse(BaseSchema):
    id: uuid.UUID
    status: str
    question: str
    title: Optional[str] = None
    brand_name: Optional[str] = None
    category: Optional[str] = None
    context: Optional[dict] = None
    study_metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    steps: Optional[dict] = None


class StudyBriefContent(BaseSchema):
    study_type: str
    study_type_confidence: float
    recommended_title: str
    recommended_metrics: list[str]
    recommended_audience: dict
    methodology_family: str
    methodology_rationale: str
    competitive_context: Optional[str] = None
    flags: list[str] = []


class StepVersionResponse(BaseSchema):
    id: uuid.UUID
    study_id: uuid.UUID
    step: int
    version: int
    status: str
    content: dict
    ai_rationale: Optional[dict] = None
    locked_at: Optional[datetime] = None
    created_at: datetime
