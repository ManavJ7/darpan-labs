"""Tests for the simplified interview pipeline.

Covers:
1. Answer satisfaction check (LLM-based)
2. Sequential question selection (static, no signal-gap scoring)
3. Module completion by question count
4. Follow-up probe generation for unsatisfactory answers
5. Max 2 consecutive follow-ups enforcement
6. Follow-up probe LLM failure graceful degradation
7. AnswerSatisfactionResponse schema
8. Simplified module state (increment only)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.llm_responses import (
    AcknowledgmentResponse,
    AdaptiveQuestionResult,
    AnswerSatisfactionResponse,
    FollowUpProbeResponse,
    ModuleCompletionResult,
)
from app.services.answer_parser_service import AnswerParserService
from app.services.question_bank_service import (
    Question,
    QuestionBankService,
)


# ============================================================
# Helpers
# ============================================================


def _make_question(question_id: str = "Q1", **kwargs) -> Question:
    """Create a test Question."""
    defaults = {
        "question_id": question_id,
        "question_text": f"Test question {question_id}",
        "question_type": "open_text",
        "target_signals": ["test_signal"],
    }
    defaults.update(kwargs)
    return Question(**defaults)


def _make_mock_qb(total_questions: int = 15, module_id: str = "M1"):
    """Create a mock QuestionBankService with N questions."""
    mock_qb = MagicMock(spec=QuestionBankService)
    questions = [_make_question(f"Q{i+1}") for i in range(total_questions)]
    mock_bank = MagicMock()
    mock_bank.questions = questions
    mock_qb.load_question_bank.return_value = mock_bank
    mock_qb.get_module_name.return_value = "Test Module"

    def _get_next_static(*args, **kwargs):
        # Accept both positional and keyword args
        asked = kwargs.get("asked_question_ids", args[1] if len(args) > 1 else [])
        for q in questions:
            if q.question_id not in asked:
                return q
        return None

    mock_qb.get_next_static_question.side_effect = _get_next_static
    mock_qb.get_first_question.return_value = questions[0]
    return mock_qb


# ============================================================
# 1. Answer Satisfaction Tests
# ============================================================


class TestAnswerSatisfaction:
    """Test the LLM-based answer satisfaction check."""

    @pytest.mark.asyncio
    async def test_satisfactory_answer(self):
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = AnswerSatisfactionResponse(
            satisfactory=True, reason=None
        )
        mock_prompt = MagicMock()
        mock_prompt.get_answer_satisfaction_prompt.return_value = "test prompt"

        service = AnswerParserService(llm_client=mock_llm, prompt_service=mock_prompt)
        is_sat, reason = await service.is_answer_satisfactory(
            "What do you do for a living?",
            "I work as a software engineer at a startup, building backend systems."
        )
        assert is_sat is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_unsatisfactory_answer(self):
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = AnswerSatisfactionResponse(
            satisfactory=False, reason="too vague"
        )
        mock_prompt = MagicMock()
        mock_prompt.get_answer_satisfaction_prompt.return_value = "test prompt"

        service = AnswerParserService(llm_client=mock_llm, prompt_service=mock_prompt)
        is_sat, reason = await service.is_answer_satisfactory(
            "Tell me about your daily routine",
            "It's okay I guess"
        )
        assert is_sat is False
        assert reason == "too vague"

    @pytest.mark.asyncio
    async def test_empty_answer_is_unsatisfactory(self):
        service = AnswerParserService(llm_client=AsyncMock(), prompt_service=MagicMock())
        is_sat, reason = await service.is_answer_satisfactory("question", "")
        assert is_sat is False
        assert reason == "empty answer"

    @pytest.mark.asyncio
    async def test_whitespace_answer_is_unsatisfactory(self):
        service = AnswerParserService(llm_client=AsyncMock(), prompt_service=MagicMock())
        is_sat, reason = await service.is_answer_satisfactory("question", "   ")
        assert is_sat is False
        assert reason == "empty answer"

    @pytest.mark.asyncio
    async def test_llm_failure_treats_as_satisfactory(self):
        mock_llm = AsyncMock()
        mock_llm.generate.side_effect = Exception("LLM down")
        mock_prompt = MagicMock()
        mock_prompt.get_answer_satisfaction_prompt.return_value = "test prompt"

        service = AnswerParserService(llm_client=mock_llm, prompt_service=mock_prompt)
        is_sat, reason = await service.is_answer_satisfactory("question", "some answer")
        assert is_sat is True
        assert reason is None


# ============================================================
# 2. Sequential Question Selection Tests
# ============================================================


class TestSequentialQuestionSelection:
    """Test that questions are selected sequentially from the bank."""

    def test_get_next_static_question_returns_first(self):
        qb = _make_mock_qb(total_questions=5)
        q = qb.get_next_static_question("M1", [])
        assert q.question_id == "Q1"

    def test_get_next_static_question_skips_asked(self):
        qb = _make_mock_qb(total_questions=5)
        q = qb.get_next_static_question("M1", ["Q1", "Q2"])
        assert q.question_id == "Q3"

    def test_get_next_static_question_returns_none_when_exhausted(self):
        qb = _make_mock_qb(total_questions=3)
        q = qb.get_next_static_question("M1", ["Q1", "Q2", "Q3"])
        assert q is None


# ============================================================
# 3. Module Completion by Question Count
# ============================================================


class TestModuleCompletionByCount:
    """Test that module completion is based on question count."""

    @pytest.mark.asyncio
    async def test_module_incomplete_when_questions_remain(self):
        from app.services.module_state_service import ModuleStateService

        mock_qb = MagicMock()
        mock_bank = MagicMock()
        mock_bank.questions = [_make_question(f"Q{i}") for i in range(15)]
        mock_qb.load_question_bank.return_value = mock_bank

        service = ModuleStateService(question_bank=mock_qb)

        mock_module = MagicMock()
        mock_module.module_id = "M1"
        mock_module.question_count = 5
        mock_module.coverage_score = 0.0
        mock_module.confidence_score = 0.0
        mock_module.signals_captured = []
        mock_module.completion_eval = {}

        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_module)
        )

        result = await service.evaluate_module_completion(mock_session, "session-id", "M1")
        assert result.is_complete is False
        assert result.recommendation == "ASK_MORE"

    @pytest.mark.asyncio
    async def test_module_complete_when_all_questions_asked(self):
        from app.services.module_state_service import ModuleStateService

        mock_qb = MagicMock()
        mock_bank = MagicMock()
        mock_bank.questions = [_make_question(f"Q{i}") for i in range(15)]
        mock_qb.load_question_bank.return_value = mock_bank

        service = ModuleStateService(question_bank=mock_qb)

        mock_module = MagicMock()
        mock_module.module_id = "M1"
        mock_module.question_count = 15
        mock_module.coverage_score = 0.0
        mock_module.confidence_score = 0.0
        mock_module.signals_captured = []
        mock_module.completion_eval = {}

        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_module)
        )

        result = await service.evaluate_module_completion(mock_session, "session-id", "M1")
        assert result.is_complete is True
        assert result.recommendation == "COMPLETE"
        assert result.coverage_score == 1.0

    @pytest.mark.asyncio
    async def test_module_complete_when_more_than_total(self):
        """Edge case: question_count exceeds total (e.g. follow-ups counted)."""
        from app.services.module_state_service import ModuleStateService

        mock_qb = MagicMock()
        mock_bank = MagicMock()
        mock_bank.questions = [_make_question(f"Q{i}") for i in range(10)]
        mock_qb.load_question_bank.return_value = mock_bank

        service = ModuleStateService(question_bank=mock_qb)

        mock_module = MagicMock()
        mock_module.module_id = "M1"
        mock_module.question_count = 12
        mock_module.coverage_score = 0.0
        mock_module.confidence_score = 0.0
        mock_module.signals_captured = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_module)
        )

        result = await service.evaluate_module_completion(mock_session, "session-id", "M1")
        assert result.is_complete is True


# ============================================================
# 4. Simplified Module State Update
# ============================================================


class TestSimplifiedModuleStateUpdate:
    """Test that update_module_after_answer just increments count."""

    @pytest.mark.asyncio
    async def test_increment_question_count(self):
        from app.services.module_state_service import ModuleStateService

        service = ModuleStateService(question_bank=MagicMock())

        mock_module = MagicMock()
        mock_module.module_id = "M1"
        mock_module.question_count = 3

        mock_session = AsyncMock()
        result = await service.update_module_after_answer(mock_session, mock_module)

        assert mock_module.question_count == 4
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_increment_from_zero(self):
        from app.services.module_state_service import ModuleStateService

        service = ModuleStateService(question_bank=MagicMock())

        mock_module = MagicMock()
        mock_module.module_id = "M1"
        mock_module.question_count = 0

        mock_session = AsyncMock()
        await service.update_module_after_answer(mock_session, mock_module)

        assert mock_module.question_count == 1


# ============================================================
# 5. Hybrid Flow: Follow-Up Path
# ============================================================


class TestHybridFollowUpPath:
    """Test that unsatisfactory answers trigger follow-up probes."""

    @pytest.mark.asyncio
    async def test_unsatisfactory_triggers_followup(self):
        from app.services.interview_service import InterviewService

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = FollowUpProbeResponse(
            acknowledgment_text="I see.",
            followup_question="Can you give me a specific example?",
            followup_intent="DEEPEN",
        )

        service = InterviewService(
            question_bank=_make_mock_qb(),
            module_state=MagicMock(),
            answer_parser=MagicMock(),
            prompt_service=MagicMock(),
            llm_client=mock_llm,
        )

        # Mock last user turn with unsatisfactory answer
        mock_turn = MagicMock()
        mock_turn.answer_meta = {"is_satisfactory": False, "unsatisfactory_reason": "too vague"}
        mock_turn.answer_text = "It's fine"
        mock_turn.question_text = "How do you make decisions?"
        mock_turn.question_meta = {"target_signal": "speed_vs_deliberation", "question_text": "How do you make decisions?"}

        mock_module = MagicMock()
        mock_module.module_id = "M2"
        mock_module.session_id = "session-id"

        mock_session = AsyncMock()

        # Patch internal methods
        service._get_last_user_turn = AsyncMock(return_value=mock_turn)
        service._count_consecutive_followups = AsyncMock(return_value=0)
        service._get_brief_context = AsyncMock(return_value="")

        result = await service._get_next_question_hybrid(mock_session, "session-id", mock_module)

        assert result.action == "ASK_FOLLOWUP"
        assert result.is_followup is True
        assert "specific example" in result.question_text


class TestHybridSatisfiedPath:
    """Test that satisfactory answers lead to next bank question."""

    @pytest.mark.asyncio
    async def test_satisfactory_gets_next_question(self):
        from app.services.interview_service import InterviewService

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = AcknowledgmentResponse(
            acknowledgment_text="Great, thanks for sharing."
        )

        mock_qb = _make_mock_qb()

        service = InterviewService(
            question_bank=mock_qb,
            module_state=MagicMock(),
            answer_parser=MagicMock(),
            prompt_service=MagicMock(),
            llm_client=mock_llm,
        )

        # Mock last user turn with satisfactory answer
        mock_turn = MagicMock()
        mock_turn.answer_meta = {"is_satisfactory": True}
        mock_turn.answer_text = "I work at a tech company building APIs"
        mock_turn.question_text = "What do you do?"
        mock_turn.question_meta = {"question_text": "What do you do?"}

        mock_module = MagicMock()
        mock_module.module_id = "M1"
        mock_module.session_id = "session-id"
        mock_module.question_count = 1

        mock_session = AsyncMock()

        service._get_last_user_turn = AsyncMock(return_value=mock_turn)
        service._count_consecutive_followups = AsyncMock(return_value=0)
        service._get_asked_question_ids = AsyncMock(return_value=["Q1"])

        result = await service._get_next_question_hybrid(mock_session, "session-id", mock_module)

        assert result.action == "ASK_QUESTION"
        assert result.question_id == "Q2"
        assert result.acknowledgment_text is not None


# ============================================================
# 6. Max 2 Consecutive Follow-Ups
# ============================================================


class TestMaxConsecutiveFollowUps:
    """Test enforcement of max 2 consecutive follow-ups."""

    @pytest.mark.asyncio
    async def test_moves_on_after_2_followups(self):
        from app.services.interview_service import InterviewService

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = AcknowledgmentResponse(
            acknowledgment_text="Okay, let's move on."
        )

        service = InterviewService(
            question_bank=_make_mock_qb(),
            module_state=MagicMock(),
            answer_parser=MagicMock(),
            prompt_service=MagicMock(),
            llm_client=mock_llm,
        )

        # Unsatisfactory answer but already 2 follow-ups
        mock_turn = MagicMock()
        mock_turn.answer_meta = {"is_satisfactory": False, "unsatisfactory_reason": "vague"}
        mock_turn.answer_text = "dunno"
        mock_turn.question_text = "Tell me more"
        mock_turn.question_meta = {"question_text": "Tell me more"}

        mock_module = MagicMock()
        mock_module.module_id = "M1"
        mock_module.session_id = "session-id"

        mock_session = AsyncMock()

        service._get_last_user_turn = AsyncMock(return_value=mock_turn)
        service._count_consecutive_followups = AsyncMock(return_value=2)
        service._get_asked_question_ids = AsyncMock(return_value=["Q1"])

        result = await service._get_next_question_hybrid(mock_session, "session-id", mock_module)

        # Should move to next bank question, not another follow-up
        assert result.action == "ASK_QUESTION"
        assert result.is_followup is False


# ============================================================
# 7. Follow-Up Probe LLM Failure
# ============================================================


class TestFollowUpProbeFailure:
    """Test graceful degradation when follow-up probe LLM fails."""

    @pytest.mark.asyncio
    async def test_falls_back_to_next_question(self):
        from app.services.interview_service import InterviewService

        mock_llm = AsyncMock()
        # First call (follow-up) fails, second call (acknowledgment) succeeds
        mock_llm.generate.side_effect = [
            Exception("LLM error"),
            AcknowledgmentResponse(acknowledgment_text="Thanks."),
        ]

        service = InterviewService(
            question_bank=_make_mock_qb(),
            module_state=MagicMock(),
            answer_parser=MagicMock(),
            prompt_service=MagicMock(),
            llm_client=mock_llm,
        )

        mock_turn = MagicMock()
        mock_turn.answer_meta = {"is_satisfactory": False, "unsatisfactory_reason": "vague"}
        mock_turn.answer_text = "meh"
        mock_turn.question_text = "test q"
        mock_turn.question_meta = {"target_signal": "sig", "question_text": "test q"}

        mock_module = MagicMock()
        mock_module.module_id = "M1"
        mock_module.session_id = "session-id"

        mock_session = AsyncMock()

        service._get_last_user_turn = AsyncMock(return_value=mock_turn)
        service._count_consecutive_followups = AsyncMock(return_value=0)
        service._get_brief_context = AsyncMock(return_value="")
        service._get_asked_question_ids = AsyncMock(return_value=["Q1"])

        result = await service._get_next_question_hybrid(mock_session, "session-id", mock_module)

        # Should fall back to next bank question
        assert result.action == "ASK_QUESTION"


# ============================================================
# 8. Schema Tests
# ============================================================


class TestAnswerSatisfactionSchema:
    """Test AnswerSatisfactionResponse schema."""

    def test_satisfactory_response(self):
        resp = AnswerSatisfactionResponse(satisfactory=True, reason=None)
        assert resp.satisfactory is True
        assert resp.reason is None

    def test_unsatisfactory_response(self):
        resp = AnswerSatisfactionResponse(satisfactory=False, reason="too brief")
        assert resp.satisfactory is False
        assert resp.reason == "too brief"

    def test_default_reason(self):
        resp = AnswerSatisfactionResponse(satisfactory=True)
        assert resp.reason is None


class TestModuleCompletionResultSimplified:
    """Test simplified ModuleCompletionResult."""

    def test_complete_result(self):
        result = ModuleCompletionResult(
            is_complete=True,
            coverage_score=1.0,
            confidence_score=1.0,
            signals_captured=[],
            signals_missing=[],
            recommendation="COMPLETE",
        )
        assert result.is_complete is True
        assert result.coverage_score == 1.0

    def test_incomplete_result(self):
        result = ModuleCompletionResult(
            is_complete=False,
            coverage_score=0.33,
            confidence_score=0.0,
            signals_captured=[],
            signals_missing=[],
            recommendation="ASK_MORE",
        )
        assert result.is_complete is False


# ============================================================
# 9. All Questions Exhausted → MODULE_COMPLETE
# ============================================================


class TestAllQuestionsExhausted:
    """Test that exhausting all questions triggers MODULE_COMPLETE."""

    @pytest.mark.asyncio
    async def test_returns_module_complete(self):
        from app.services.interview_service import InterviewService

        mock_qb = _make_mock_qb(total_questions=3)

        service = InterviewService(
            question_bank=mock_qb,
            module_state=MagicMock(),
            answer_parser=MagicMock(),
            prompt_service=MagicMock(),
            llm_client=AsyncMock(),
        )

        mock_turn = MagicMock()
        mock_turn.answer_meta = {"is_satisfactory": True}
        mock_turn.answer_text = "Good answer"
        mock_turn.question_text = "Last question"

        mock_module = MagicMock()
        mock_module.module_id = "M1"
        mock_module.session_id = "session-id"

        mock_session = AsyncMock()

        service._get_last_user_turn = AsyncMock(return_value=mock_turn)
        service._count_consecutive_followups = AsyncMock(return_value=0)
        service._get_asked_question_ids = AsyncMock(return_value=["Q1", "Q2", "Q3"])

        result = await service._get_next_question_hybrid(mock_session, "session-id", mock_module)

        assert result.action == "MODULE_COMPLETE"
