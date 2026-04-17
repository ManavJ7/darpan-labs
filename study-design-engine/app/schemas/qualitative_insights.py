from app.schemas.common import BaseSchema


class ThemeItem(BaseSchema):
    theme_name: str
    frequency: int
    frequency_pct: float
    sentiment: str  # positive, negative, neutral, mixed
    representative_quote: str


class ConceptInsight(BaseSchema):
    concept_index: int
    concept_name: str
    question_type: str  # "appealing" or "improve"
    question_text: str
    summary: str
    themes: list[ThemeItem]
    representative_quotes: list[str]
    response_count: int


class QualitativeInsightsResponse(BaseSchema):
    study_id: str
    insights: list[ConceptInsight]
    generated_at: str
    cached: bool
