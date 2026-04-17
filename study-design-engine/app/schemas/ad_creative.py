"""Schemas for Ad Creative Testing — creative territory structure and responses."""

from typing import Optional
from app.schemas.common import BaseSchema


# ─── Tone & Emotion Options ────────────────────────────

TONE_MOOD_OPTIONS = [
    "Aspirational", "Humorous", "Emotional/Heartfelt", "Bold/Disruptive",
    "Authoritative", "Warm/Reassuring", "Edgy", "Nostalgic", "Energetic",
]

TARGET_EMOTION_OPTIONS = [
    "Pride", "Warmth", "Curiosity", "Inspiration", "Reassurance",
    "Excitement", "Nostalgia", "Amusement", "Empowerment", "Belonging",
]

# ─── KPI Module Definitions ────────────────────────────

KPI_MODULES = {
    "M1_distinctiveness": {
        "name": "Distinctiveness",
        "questions": 5,
        "description": "How different, fresh, and memorable the idea feels",
    },
    "M2_message_clarity": {
        "name": "Message Clarity",
        "questions": 4,
        "description": "Message takeout, comprehension, confusion check",
    },
    "M3_relevance_resonance": {
        "name": "Relevance & Resonance",
        "questions": 4,
        "description": "Personal relevance, real-need alignment, stopping power",
    },
    "M4_emotional_signature": {
        "name": "Emotional Signature",
        "questions": 8,
        "description": "12-descriptor emotional evaluation across 4 quadrants",
    },
    "M5_brand_fit_persuasion": {
        "name": "Brand Fit & Persuasion",
        "questions": 5,
        "description": "Brand expectation fit, persuasion shift, personality match",
    },
    "M6_competitive_misattribution": {
        "name": "Competitive Misattribution",
        "questions": 3,
        "description": "Which competitor could run this? Is it ownable?",
    },
}

# ─── Emotional Signature Descriptors ───────────────────

EMOTIONAL_DESCRIPTORS = {
    "active_positive": ["Involving", "Interesting", "Distinctive"],
    "passive_positive": ["Soothing", "Pleasant", "Gentle"],
    "passive_negative": ["Weak", "Dull", "Boring"],
    "active_negative": ["Irritating", "Unpleasant", "Disturbing"],
}

# ─── Campaign Objective → ISS Weights ──────────────────

ISS_WEIGHTS = {
    "default":              {"in_market_impact": 0.30, "engagement": 0.25, "brand_predisposition": 0.30, "associations": 0.15},
    "brand_building":       {"in_market_impact": 0.25, "engagement": 0.25, "brand_predisposition": 0.30, "associations": 0.20},
    "product_launch":       {"in_market_impact": 0.35, "engagement": 0.20, "brand_predisposition": 0.35, "associations": 0.10},
    "promotional_tactical": {"in_market_impact": 0.40, "engagement": 0.20, "brand_predisposition": 0.30, "associations": 0.10},
    "repositioning":        {"in_market_impact": 0.25, "engagement": 0.20, "brand_predisposition": 0.30, "associations": 0.25},
    "awareness":            {"in_market_impact": 0.35, "engagement": 0.25, "brand_predisposition": 0.25, "associations": 0.15},
    "category_entry":       {"in_market_impact": 0.30, "engagement": 0.25, "brand_predisposition": 0.30, "associations": 0.15},
}

# ─── Territory Component Schema ─────────────────────────

class TerritoryComponent(BaseSchema):
    raw_input: str = ""
    refined: Optional[str] = None
    refinement_rationale: Optional[str] = None
    approved: bool = False
    brand_edit: Optional[str] = None


class TerritoryComponents(BaseSchema):
    territory_name: TerritoryComponent
    core_insight: TerritoryComponent
    big_idea: TerritoryComponent
    key_message: TerritoryComponent
    tone_mood: str = ""  # single-select, not refinable
    execution_sketch: TerritoryComponent
    target_emotion: list[str] = []  # multi-select, not refinable


class TerritoryRefineResponse(BaseSchema):
    territory_id: str
    refined_components: dict
    flags: list[str]
    testability_score: float
    distinctiveness_warning: Optional[str] = None


# ─── ISS Verdict ────────────────────────────────────────

ISS_VERDICT_BANDS = {
    "develop": (70, 100),
    "refine": (50, 69),
    "park": (0, 49),
}


def iss_verdict(score: float) -> str:
    if score >= 70:
        return "develop"
    if score >= 50:
        return "refine"
    return "park"
