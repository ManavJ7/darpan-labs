"""Pydantic schemas for LLM responses.

These schemas are used with the LLM client's response_format parameter
to validate and parse LLM JSON outputs.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class NarrativeSnippet(BaseModel):
    """A quote-worthy phrase from the user's answer."""

    text: str = Field(description="Exact or near-exact quote from user")
    category: Literal[
        "anecdote", "self_description", "rule_of_thumb",
        "preference_statement", "emotional_reveal"
    ] = Field(description="Type of narrative snippet")


class StyleMarker(BaseModel):
    """A communication style observation."""

    marker: str = Field(description="Style marker, e.g. 'uses_analogies', 'hedges_frequently'")
    evidence: str = Field(description="Brief quote supporting this observation")


class OpenLoop(BaseModel):
    """An unresolved conversational thread worth revisiting."""

    topic: str = Field(description="What the thread is about")
    reason: str = Field(description="Why it's worth revisiting")
    source_signal: str = Field(default="", description="Related signal if any")


class ExtractedSignal(BaseModel):
    """A signal extracted from an answer."""

    signal: str = Field(description="Name of the signal extracted")
    value: str = Field(description="Value or summary of what was learned")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence in this extraction (0-1)"
    )


class BehavioralRule(BaseModel):
    """A behavioral rule extracted from an answer."""

    rule: str = Field(description="Behavioral rule in 'if X then Y' format")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this rule (0-1)")


class BehavioralRuleWithEvidence(BaseModel):
    """Behavioral rule with evidence references."""

    rule: str = Field(description="Behavioral rule statement")
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_turn_ids: list[str] = Field(
        default_factory=list, description="Turn IDs supporting this rule"
    )


class ParsedAnswerResponse(BaseModel):
    """LLM response from answer_parser.txt prompt.

    Used to analyze user answers and extract signals.
    """

    specificity_score: float = Field(
        ge=0.0,
        le=1.0,
        description="How specific/detailed the answer is (0=vague, 1=very specific)",
    )
    signals_extracted: list[ExtractedSignal] = Field(
        default_factory=list, description="Signals extracted from this answer"
    )
    behavioral_rules: list[BehavioralRule] = Field(
        default_factory=list, description="Behavioral rules identified"
    )
    needs_followup: bool = Field(
        default=False, description="Whether a follow-up question is needed"
    )
    followup_reason: Literal["vague", "contradiction", "high_leverage", None] = Field(
        default=None, description="Reason for follow-up if needed"
    )
    sentiment: Literal["positive", "neutral", "negative", "mixed"] = Field(
        default="neutral", description="Overall sentiment of the answer"
    )
    language_detected: Literal["EN", "HI", "HG"] = Field(
        default="EN", description="Detected language (EN=English, HI=Hindi, HG=Hinglish)"
    )
    narrative_snippets: list[NarrativeSnippet] = Field(
        default_factory=list, description="Quote-worthy phrases from the answer"
    )
    style_markers: list[StyleMarker] = Field(
        default_factory=list, description="Communication style observations"
    )
    exceptions_mentioned: list[str] = Field(
        default_factory=list, description="'except when...' / 'unless...' patterns"
    )
    contradiction_candidates: list[str] = Field(
        default_factory=list, description="Potential contradictions with earlier answers"
    )
    self_descriptors: list[str] = Field(
        default_factory=list, description="'I'm the kind of person who...' statements"
    )
    open_loops: list[OpenLoop] = Field(
        default_factory=list, description="Unresolved threads worth revisiting"
    )
    exemplar_quality: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="How good this answer is for twin training (0-1)"
    )

    @field_validator("followup_reason", mode="before")
    @classmethod
    def normalize_null_string(cls, v: Any) -> str | None:
        """LLMs sometimes return the string 'null' instead of JSON null."""
        if isinstance(v, str) and v.lower() == "null":
            return None
        return v


class ModuleCompletionResponse(BaseModel):
    """LLM response from module_completion.txt prompt.

    Used to evaluate if a module has reached completion criteria.
    """

    module_id: str = Field(description="Module being evaluated")
    is_complete: bool = Field(description="Whether module meets completion criteria")
    coverage_score: float = Field(
        ge=0.0, le=1.0, description="Proportion of target signals covered"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Overall confidence in captured data"
    )
    signals_captured: list[str] = Field(
        default_factory=list, description="Signal names that have been captured"
    )
    signals_missing: list[str] = Field(
        default_factory=list, description="Signal names still needed"
    )
    behavioral_rules_extracted: list[BehavioralRuleWithEvidence] = Field(
        default_factory=list, description="Behavioral rules with evidence"
    )
    recommendation: Literal["COMPLETE", "ASK_MORE", "SKIP_OPTIONAL"] = Field(
        description="Recommended action"
    )
    suggested_next_questions: list[str] = Field(
        default_factory=list, description="Suggested questions if ASK_MORE"
    )
    module_summary: str | None = Field(
        default=None, description="Summary of what was learned (if COMPLETE)"
    )
    narrative_depth_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="How many concrete episodes/anecdotes were captured (0-1)"
    )
    style_coverage_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Can we replicate their voice? (0-1)"
    )
    contradiction_count: int = Field(
        default=0, ge=0,
        description="Number of discovered tensions (positive for realism)"
    )
    twin_readiness_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Composite: 0.4*coverage + 0.25*confidence + 0.2*narrative + 0.15*style"
    )


class AdaptiveQuestionResponse(BaseModel):
    """LLM response from interviewer_question.txt prompt.

    Used to generate the next adaptive question.
    """

    action: Literal["ASK_QUESTION", "ASK_FOLLOWUP", "MODULE_COMPLETE", "OFFER_BREAK"] = (
        Field(description="What action to take")
    )
    acknowledgment_text: str | None = Field(
        default=None,
        description="Brief acknowledgment of user's previous answer",
    )
    question_text: str = Field(description="The question to ask (always in English)")
    question_text_hindi: str | None = Field(
        default=None, description="Deprecated — kept for backwards compat, always None"
    )
    language: Literal["EN", "HI", "HG"] = Field(
        default="EN", description="Always EN — kept for backwards compat"
    )
    question_type: str = Field(description="Type of question")
    target_signal: str = Field(description="Signal this question targets")
    rationale_short: str = Field(description="Brief rationale for asking this question")
    question_intent: Literal["EXPLORE", "DEEPEN", "CONTRAST", "CLARIFY", "RESOLVE"] = Field(
        default="EXPLORE", description="Intent behind this question"
    )
    module_summary: str | None = Field(
        default=None, description="Summary if MODULE_COMPLETE"
    )


# Internal service models (not for LLM response parsing)


class ParsedAnswer(BaseModel):
    """Internal representation of a parsed answer."""

    specificity_score: float
    signals_extracted: list[ExtractedSignal]
    behavioral_rules: list[BehavioralRule]
    needs_followup: bool
    followup_reason: str | None
    sentiment: str
    language: str
    narrative_snippets: list[NarrativeSnippet] = Field(default_factory=list)
    style_markers: list[StyleMarker] = Field(default_factory=list)
    exceptions_mentioned: list[str] = Field(default_factory=list)
    contradiction_candidates: list[str] = Field(default_factory=list)
    self_descriptors: list[str] = Field(default_factory=list)
    open_loops: list[OpenLoop] = Field(default_factory=list)
    exemplar_quality: float = 0.5

    @classmethod
    def from_llm_response(cls, response: ParsedAnswerResponse) -> "ParsedAnswer":
        """Create from LLM response."""
        return cls(
            specificity_score=response.specificity_score,
            signals_extracted=response.signals_extracted,
            behavioral_rules=response.behavioral_rules,
            needs_followup=response.needs_followup,
            followup_reason=response.followup_reason,
            sentiment=response.sentiment,
            language=response.language_detected,
            narrative_snippets=response.narrative_snippets,
            style_markers=response.style_markers,
            exceptions_mentioned=response.exceptions_mentioned,
            contradiction_candidates=response.contradiction_candidates,
            self_descriptors=response.self_descriptors,
            open_loops=response.open_loops,
            exemplar_quality=response.exemplar_quality,
        )


class ModuleCompletionResult(BaseModel):
    """Internal result of module completion evaluation."""

    is_complete: bool
    coverage_score: float
    confidence_score: float
    signals_captured: list[str]
    signals_missing: list[str]
    recommendation: str
    module_summary: str | None = None
    suggested_questions: list[str] = Field(default_factory=list)
    narrative_depth_score: float = 0.0
    style_coverage_score: float = 0.0
    contradiction_count: int = 0
    twin_readiness_score: float = 0.0

    @classmethod
    def from_llm_response(cls, response: ModuleCompletionResponse) -> "ModuleCompletionResult":
        """Create from LLM response."""
        return cls(
            is_complete=response.is_complete,
            coverage_score=response.coverage_score,
            confidence_score=response.confidence_score,
            signals_captured=response.signals_captured,
            signals_missing=response.signals_missing,
            recommendation=response.recommendation,
            module_summary=response.module_summary,
            suggested_questions=response.suggested_next_questions,
            narrative_depth_score=response.narrative_depth_score,
            style_coverage_score=response.style_coverage_score,
            contradiction_count=response.contradiction_count,
            twin_readiness_score=response.twin_readiness_score,
        )


class CorrectedTranscript(BaseModel):
    """LLM response from transcript_correction.txt prompt.

    Used to correct ASR transcripts and tag language segments.
    """

    corrected_transcript: str = Field(description="Corrected transcript text")
    language_tags: list[dict] = Field(
        default_factory=list,
        description="Language tags per segment [{start, end, lang}]",
    )
    primary_language: Literal["EN", "HI", "HG"] = Field(
        default="EN", description="Primary language of the transcript"
    )
    correction_applied: bool = Field(
        default=False, description="Whether any corrections were applied"
    )
    corrections: list[dict] = Field(
        default_factory=list,
        description="List of corrections [{original, corrected, reason}]",
    )


class AnswerSatisfactionResponse(BaseModel):
    """LLM response from answer_satisfaction.txt prompt.

    Used to judge if a user's answer is satisfactory or needs follow-up.
    """

    satisfactory: bool = Field(description="Whether the answer is satisfactory")
    reason: str | None = Field(
        default=None, description="Reason if not satisfactory"
    )


class FollowUpProbeResponse(BaseModel):
    """LLM response from followup_probe.txt prompt.

    Used when the user gives a vague answer and we need to probe deeper.
    """

    acknowledgment_text: str = Field(
        description="1-2 sentences referencing the user's answer"
    )
    followup_question: str = Field(
        description="Targeted probe for detail"
    )
    followup_intent: Literal["DEEPEN", "CLARIFY"] = Field(
        default="DEEPEN", description="Intent behind the follow-up"
    )


class AcknowledgmentResponse(BaseModel):
    """LLM response from acknowledgment.txt prompt.

    Used for warm transitions between satisfied answers and the next question.
    """

    acknowledgment_text: str = Field(
        description="Brief warm acknowledgment of the user's answer"
    )


class AdaptiveQuestionResult(BaseModel):
    """Internal result of adaptive question generation."""

    action: str
    question_text: str
    question_text_hindi: str | None = None
    language: str
    question_type: str
    target_signal: str
    rationale: str
    question_intent: str = "EXPLORE"
    module_summary: str | None = None
    acknowledgment_text: str | None = None
    is_followup: bool = False
    question_id: str | None = None  # Static question ID if using fallback

    @classmethod
    def from_llm_response(cls, response: AdaptiveQuestionResponse) -> "AdaptiveQuestionResult":
        """Create from LLM response."""
        # Normalize question_type to match expected values
        QUESTION_TYPE_MAP = {
            "tradeoff": "trade_off",
            "trade-off": "trade_off",
            "clarification": "open_text",
            "follow_up": "open_text",
            "followup": "open_text",
            "forced_choice": "single_select",
            "likert": "scale",
        }
        VALID_TYPES = {
            "open_text", "numeric", "single_select", "multi_select",
            "scale", "scale_open", "rank_order", "matrix_scale", "matrix_premium",
            # Legacy types
            "forced_choice", "scenario", "trade_off", "likert",
        }
        q_type = response.question_type.lower().strip()
        q_type = QUESTION_TYPE_MAP.get(q_type, q_type)
        if q_type not in VALID_TYPES:
            q_type = "open_text"

        # Normalize question_intent
        VALID_INTENTS = {"EXPLORE", "DEEPEN", "CONTRAST", "CLARIFY", "RESOLVE"}
        intent = response.question_intent.upper().strip()
        if intent not in VALID_INTENTS:
            intent = "EXPLORE"

        return cls(
            action=response.action,
            question_text=response.question_text,
            question_text_hindi=response.question_text_hindi,
            language=response.language,
            question_type=q_type,
            target_signal=response.target_signal,
            rationale=response.rationale_short,
            question_intent=intent,
            module_summary=response.module_summary,
            acknowledgment_text=response.acknowledgment_text,
            is_followup=response.action == "ASK_FOLLOWUP",
        )
