from typing import Optional

from app.schemas.common import BaseSchema


class MetricResponse(BaseSchema):
    id: str
    display_name: str
    category: str
    description: Optional[str] = None
    applicable_study_types: list[str]
    default_scale: dict
    benchmark_available: bool


class MetricCreate(BaseSchema):
    id: str
    display_name: str
    category: str
    description: Optional[str] = None
    applicable_study_types: list[str]
    default_scale: dict
    benchmark_available: bool = False
