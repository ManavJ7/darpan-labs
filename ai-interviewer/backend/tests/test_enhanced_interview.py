"""Tests for interview system schemas, question bank, and prompt loading."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.llm_responses import (
    AdaptiveQuestionResponse,
    AdaptiveQuestionResult,
    BehavioralRule,
    ExtractedSignal,
    ModuleCompletionResponse,
    ModuleCompletionResult,
    NarrativeSnippet,
    OpenLoop,
    ParsedAnswer,
    ParsedAnswerResponse,
    StyleMarker,
)
from app.services.prompt_service import PromptService
from app.services.question_bank_service import Question


# ============================================================
# 1. Schema Tests
# ============================================================


class TestNewSchemaModels:
    """Test Pydantic models and extended fields."""

    def test_narrative_snippet_valid(self):
        ns = NarrativeSnippet(text="I quit my job last year", category="anecdote")
        assert ns.text == "I quit my job last year"
        assert ns.category == "anecdote"

    def test_narrative_snippet_all_categories(self):
        for cat in ["anecdote", "self_description", "rule_of_thumb",
                     "preference_statement", "emotional_reveal"]:
            ns = NarrativeSnippet(text="test", category=cat)
            assert ns.category == cat

    def test_narrative_snippet_invalid_category(self):
        with pytest.raises(Exception):
            NarrativeSnippet(text="test", category="invalid")

    def test_style_marker_valid(self):
        sm = StyleMarker(marker="hedges_frequently", evidence="pretty, kind of")
        assert sm.marker == "hedges_frequently"
        assert sm.evidence == "pretty, kind of"

    def test_open_loop_valid(self):
        ol = OpenLoop(topic="startup role", reason="didn't explain why they left")
        assert ol.topic == "startup role"
        assert ol.source_signal == ""

    def test_open_loop_with_signal(self):
        ol = OpenLoop(topic="spending habits", reason="vague", source_signal="price_vs_quality")
        assert ol.source_signal == "price_vs_quality"

    def test_parsed_answer_response_defaults(self):
        """All new fields have defaults — backward compat with existing LLM responses."""
        response = ParsedAnswerResponse(
            specificity_score=0.5,
            signals_extracted=[],
            needs_followup=False,
            sentiment="neutral",
        )
        assert response.narrative_snippets == []
        assert response.style_markers == []
        assert response.exceptions_mentioned == []
        assert response.contradiction_candidates == []
        assert response.self_descriptors == []
        assert response.open_loops == []
        assert response.exemplar_quality == 0.5

    def test_parsed_answer_response_full(self):
        response = ParsedAnswerResponse(
            specificity_score=0.85,
            signals_extracted=[
                ExtractedSignal(signal="risk_appetite", value="high", confidence=0.9)
            ],
            behavioral_rules=[
                BehavioralRule(rule="if reversible then fast", confidence=0.8)
            ],
            needs_followup=False,
            sentiment="positive",
            narrative_snippets=[
                NarrativeSnippet(text="I quit my job", category="anecdote")
            ],
            style_markers=[
                StyleMarker(marker="storyteller", evidence="told vivid story")
            ],
            exceptions_mentioned=["except for books"],
            contradiction_candidates=["said risk-averse but quit job"],
            self_descriptors=["I'm pretty methodical"],
            open_loops=[
                OpenLoop(topic="startup role", reason="didn't elaborate")
            ],
            exemplar_quality=0.9,
        )
        assert len(response.narrative_snippets) == 1
        assert len(response.style_markers) == 1
        assert response.exemplar_quality == 0.9

    def test_parsed_answer_from_llm_response_maps_new_fields(self):
        response = ParsedAnswerResponse(
            specificity_score=0.7,
            signals_extracted=[],
            needs_followup=False,
            sentiment="neutral",
            narrative_snippets=[
                NarrativeSnippet(text="test quote", category="anecdote")
            ],
            style_markers=[
                StyleMarker(marker="verbose", evidence="long answer")
            ],
            exceptions_mentioned=["unless tired"],
            contradiction_candidates=["contradiction 1"],
            self_descriptors=["I'm careful"],
            open_loops=[
                OpenLoop(topic="career change", reason="hinted but didn't explain")
            ],
            exemplar_quality=0.8,
        )
        parsed = ParsedAnswer.from_llm_response(response)
        assert len(parsed.narrative_snippets) == 1
        assert parsed.narrative_snippets[0].text == "test quote"
        assert len(parsed.style_markers) == 1
        assert parsed.style_markers[0].marker == "verbose"
        assert parsed.exceptions_mentioned == ["unless tired"]
        assert parsed.contradiction_candidates == ["contradiction 1"]
        assert parsed.self_descriptors == ["I'm careful"]
        assert len(parsed.open_loops) == 1
        assert parsed.exemplar_quality == 0.8


class TestAdaptiveQuestionIntent:
    """Test question intent on AdaptiveQuestionResponse/Result."""

    def test_adaptive_question_response_default_intent(self):
        response = AdaptiveQuestionResponse(
            action="ASK_QUESTION",
            question_text="Tell me about your day",
            question_type="open_text",
            target_signal="daily_routine_pattern",
            rationale_short="exploration",
        )
        assert response.question_intent == "EXPLORE"

    def test_adaptive_question_response_with_intent(self):
        response = AdaptiveQuestionResponse(
            action="ASK_QUESTION",
            question_text="You said X but now Y",
            question_type="open_text",
            target_signal="risk_appetite",
            rationale_short="contradiction",
            question_intent="CLARIFY",
        )
        assert response.question_intent == "CLARIFY"

    def test_adaptive_question_result_maps_intent(self):
        response = AdaptiveQuestionResponse(
            action="ASK_QUESTION",
            question_text="Walk me through last time",
            question_type="open_text",
            target_signal="speed_vs_deliberation",
            rationale_short="deepen",
            question_intent="DEEPEN",
        )
        result = AdaptiveQuestionResult.from_llm_response(response)
        assert result.question_intent == "DEEPEN"

    def test_adaptive_question_response_rejects_invalid_intent(self):
        with pytest.raises(Exception):
            AdaptiveQuestionResponse(
                action="ASK_QUESTION",
                question_text="test",
                question_type="open_text",
                target_signal="test",
                rationale_short="test",
                question_intent="INVALID_INTENT",
            )

    def test_adaptive_question_result_default_intent(self):
        result = AdaptiveQuestionResult(
            action="ASK_QUESTION",
            question_text="test",
            language="EN",
            question_type="open_text",
            target_signal="test",
            rationale="test",
        )
        assert result.question_intent == "EXPLORE"


class TestModuleCompletionMultiFactor:
    """Test multi-factor fields on ModuleCompletionResponse/Result."""

    def test_module_completion_response_defaults(self):
        response = ModuleCompletionResponse(
            module_id="M1",
            is_complete=True,
            coverage_score=0.8,
            confidence_score=0.7,
            recommendation="COMPLETE",
        )
        assert response.narrative_depth_score == 0.0
        assert response.style_coverage_score == 0.0
        assert response.contradiction_count == 0
        assert response.twin_readiness_score == 0.0

    def test_module_completion_result_from_llm_maps_new_fields(self):
        response = ModuleCompletionResponse(
            module_id="M1",
            is_complete=True,
            coverage_score=0.9,
            confidence_score=0.8,
            recommendation="COMPLETE",
            narrative_depth_score=0.75,
            style_coverage_score=0.65,
            contradiction_count=3,
            twin_readiness_score=0.78,
        )
        result = ModuleCompletionResult.from_llm_response(response)
        assert result.narrative_depth_score == 0.75
        assert result.style_coverage_score == 0.65
        assert result.contradiction_count == 3
        assert result.twin_readiness_score == 0.78


# ============================================================
# 2. Prompt Tests
# ============================================================


class TestPromptEnhancements:
    """Test that prompts load and format correctly."""

    def test_interviewer_prompt_includes_conversation_state(self):
        service = PromptService()
        conversation_state = {"open_loops": [{"topic": "career"}], "style_hypothesis": []}
        prompt = service.get_interviewer_question_prompt(
            module_id="M1",
            module_name="Core Identity",
            module_goal="Understand who they are",
            signal_targets=["occupation", "age_band"],
            questions_asked=3,
            max_questions=15,
            coverage=0.4,
            confidence=0.5,
            captured_signals=["occupation"],
            missing_signals=["age_band"],
            recent_turns=[],
            cross_module_summary="No modules completed.",
            sensitivity_settings={},
            conversation_state=conversation_state,
        )
        assert "career" in prompt
        assert "open_loops" in prompt

    def test_answer_satisfaction_prompt_loads(self):
        service = PromptService()
        prompt = service.load_prompt("answer_satisfaction")
        assert "satisfactory" in prompt
        assert "question_text" in prompt or "{question_text}" in prompt

    def test_answer_satisfaction_prompt_formats(self):
        service = PromptService()
        prompt = service.get_answer_satisfaction_prompt(
            question_text="What's your morning routine?",
            answer_text="I wake up early.",
        )
        assert "morning routine" in prompt
        assert "wake up early" in prompt

    def test_followup_probe_prompt_loads(self):
        service = PromptService()
        prompt = service.load_prompt("followup_probe")
        assert "follow-up" in prompt.lower() or "followup" in prompt.lower() or "probe" in prompt.lower()

    def test_acknowledgment_prompt_loads(self):
        service = PromptService()
        prompt = service.load_prompt("acknowledgment")
        assert "acknowledgment" in prompt.lower() or "answer" in prompt.lower()


# ============================================================
# 3. Question Bank Intent Tests
# ============================================================


class TestQuestionBankIntent:
    """Test optional intent field on Question model."""

    def test_question_defaults_to_explore(self):
        q = Question(
            question_id="test_q1",
            question_text="Tell me about yourself",
            question_type="open_text",
            target_signals=["self_described_personality"],
        )
        assert q.intent == "EXPLORE"

    def test_question_with_explicit_intent(self):
        q = Question(
            question_id="test_q2",
            question_text="You mentioned X but also Y...",
            question_type="open_text",
            target_signals=["risk_appetite"],
            intent="CLARIFY",
        )
        assert q.intent == "CLARIFY"

    def test_question_all_intents_valid(self):
        for intent in ["EXPLORE", "DEEPEN", "CONTRAST", "CLARIFY", "RESOLVE"]:
            q = Question(
                question_id="test",
                question_text="test",
                question_type="open_text",
                target_signals=["test"],
                intent=intent,
            )
            assert q.intent == intent

    def test_question_invalid_intent_rejected(self):
        with pytest.raises(Exception):
            Question(
                question_id="test",
                question_text="test",
                question_type="open_text",
                target_signals=["test"],
                intent="INVALID",
            )
