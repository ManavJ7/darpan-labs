"""Schemas for the Product Brief (Step 2 of ad_creative_testing)."""

from typing import Optional
from app.schemas.common import BaseSchema


class ProductBriefContent(BaseSchema):
    """The Product Brief captures WHAT is being advertised.

    Inserted between Study Brief (step 1) and Ad Territories (step 3) in the
    ad_creative_testing flow to ground twin evaluations with product context.

    Minimal, user-authored fields. AI can refine text but does not invent.
    """
    product_name: str = ""
    category: str = ""
    target_audience_description: str = ""
    key_features: list[str] = []          # 3-5 items
    key_differentiator: str = ""
    must_communicate: str = ""


class ProductBriefRefinedField(BaseSchema):
    raw_input: str
    refined: str
    refinement_rationale: str


class ProductBriefRefineResponse(BaseSchema):
    """What the refiner returns: refined text for each refinable field + flags."""
    refined_fields: dict[str, ProductBriefRefinedField]
    flags: list[str] = []
