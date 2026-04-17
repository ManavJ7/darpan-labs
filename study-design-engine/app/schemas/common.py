from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict


class StudyStatus(str, Enum):
    init = "init"
    step_1_draft = "step_1_draft"
    step_1_review = "step_1_review"
    step_1_locked = "step_1_locked"
    step_2_draft = "step_2_draft"
    step_2_review = "step_2_review"
    step_2_locked = "step_2_locked"
    step_3_draft = "step_3_draft"
    step_3_review = "step_3_review"
    step_3_locked = "step_3_locked"
    step_4_draft = "step_4_draft"
    step_4_review = "step_4_review"
    step_4_locked = "step_4_locked"
    # Step 5 only applies to ad_creative_testing
    step_5_draft = "step_5_draft"
    step_5_review = "step_5_review"
    step_5_locked = "step_5_locked"
    complete = "complete"


class StepStatus(str, Enum):
    draft = "draft"
    review = "review"
    locked = "locked"


class ConceptStatus(str, Enum):
    raw = "raw"
    refined = "refined"
    approved = "approved"


class StudyType(str, Enum):
    concept_screening = "concept_screening"
    concept_testing = "concept_testing"
    claims_optimization = "claims_optimization"
    brand_positioning = "brand_positioning"
    price_sensitivity = "price_sensitivity"
    portfolio_optimization = "portfolio_optimization"
    ad_creative_testing = "ad_creative_testing"
    customer_segmentation = "customer_segmentation"
    category_entry = "category_entry"


class MethodologyFamily(str, Enum):
    monadic = "monadic"
    sequential_monadic = "sequential_monadic"
    proto_monadic = "proto_monadic"
    maxdiff = "maxdiff"
    conjoint_lite = "conjoint_lite"
    van_westendorp = "van_westendorp"
    gabor_granger = "gabor_granger"
    perceptual_mapping = "perceptual_mapping"


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


T = TypeVar("T")


class PaginatedRequest(BaseSchema):
    page: int = 1
    page_size: int = 20


class PaginatedResponse(BaseSchema, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
