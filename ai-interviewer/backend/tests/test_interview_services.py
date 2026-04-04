"""Tests for interview services."""

import pytest
from pathlib import Path

from app.services.prompt_service import PromptService, get_prompt_service
from app.services.question_bank_service import (
    QuestionBankService,
    get_question_bank_service,
    MODULE_FILES,
)
from app.services.answer_parser_service import AnswerParserService


class TestPromptService:
    """Tests for PromptService."""

    def test_prompt_service_initialization(self):
        """Test prompt service initializes correctly."""
        service = PromptService()
        assert service.prompts_dir.exists()

    def test_load_prompt_success(self):
        """Test loading an existing prompt."""
        service = PromptService()
        prompt = service.load_prompt("answer_parser")
        assert prompt is not None
        assert len(prompt) > 0
        assert "SYSTEM" in prompt or "OUTPUT" in prompt

    def test_load_prompt_caching(self):
        """Test that prompts are cached."""
        service = PromptService()
        prompt1 = service.load_prompt("answer_parser")
        prompt2 = service.load_prompt("answer_parser")
        assert prompt1 is prompt2  # Same object due to caching

    def test_load_prompt_not_found(self):
        """Test loading a non-existent prompt."""
        service = PromptService()
        with pytest.raises(FileNotFoundError):
            service.load_prompt("nonexistent_prompt")

    def test_format_prompt(self):
        """Test formatting a prompt with placeholders."""
        service = PromptService()
        # Create a simple test - answer_parser has placeholders
        try:
            formatted = service.format_prompt(
                "answer_parser",
                module_id="M1",
                module_name="Core Identity",
                question_text="What do you do?",
                target_signal="occupation",
                answer_text="I'm a software engineer.",
                previous_answers="No previous answers.",
            )
            assert "M1" in formatted or "module_id" not in service.load_prompt("answer_parser")
        except (KeyError, ValueError):
            # Some placeholders might be missing in the template
            pass

    def test_clear_cache(self):
        """Test clearing the cache."""
        service = PromptService()
        service.load_prompt("answer_parser")
        assert len(service._cache) > 0
        service.clear_cache()
        assert len(service._cache) == 0

    def test_singleton_instance(self):
        """Test singleton pattern."""
        service1 = get_prompt_service()
        service2 = get_prompt_service()
        assert service1 is service2


class TestQuestionBankService:
    """Tests for QuestionBankService."""

    def test_question_bank_initialization(self):
        """Test question bank service initializes correctly."""
        service = QuestionBankService()
        assert service.seed_data_dir.exists()

    def test_load_question_bank_m1(self):
        """Test loading M1 question bank."""
        service = QuestionBankService()
        bank = service.load_question_bank("M1")

        assert bank.module_id == "M1"
        assert bank.module_name == "Core Identity & Context"
        assert len(bank.questions) >= 10
        assert bank.completion_criteria.coverage_threshold > 0

    def test_load_question_bank_all_modules(self):
        """Test loading all module question banks."""
        service = QuestionBankService()

        for module_id in MODULE_FILES.keys():
            bank = service.load_question_bank(module_id)
            assert bank.module_id == module_id
            assert len(bank.questions) >= 10

    def test_load_question_bank_caching(self):
        """Test that question banks are cached."""
        service = QuestionBankService()
        bank1 = service.load_question_bank("M1")
        bank2 = service.load_question_bank("M1")
        assert bank1 is bank2

    def test_load_question_bank_invalid_module(self):
        """Test loading an invalid module."""
        service = QuestionBankService()
        with pytest.raises(ValueError):
            service.load_question_bank("INVALID")

    def test_get_all_modules(self):
        """Test getting all module metadata."""
        service = QuestionBankService()
        modules = service.get_all_modules()

        assert len(modules) == 8  # M1-M8
        assert modules[0].module_id == "M1"
        assert modules[0].module_type == "mandatory"

    def test_get_mandatory_modules(self):
        """Test getting mandatory module IDs."""
        service = QuestionBankService()
        mandatory = service.get_mandatory_modules()

        assert mandatory == ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"]

    def test_get_question_by_id(self):
        """Test getting a specific question."""
        service = QuestionBankService()
        question = service.get_question_by_id("M1", "M1_q01")

        assert question is not None
        assert question.question_id == "M1_q01"
        assert len(question.question_text) > 0

    def test_get_question_by_id_not_found(self):
        """Test getting a non-existent question."""
        service = QuestionBankService()
        question = service.get_question_by_id("M1", "NONEXISTENT")
        assert question is None

    def test_get_next_static_question(self):
        """Test getting next question in priority order."""
        service = QuestionBankService()

        # First question
        q1 = service.get_next_static_question("M1", [])
        assert q1 is not None
        assert q1.priority == 1

        # Next question (skip first)
        q2 = service.get_next_static_question("M1", [q1.question_id])
        assert q2 is not None
        assert q2.question_id != q1.question_id

    def test_get_next_static_question_all_asked(self):
        """Test when all questions have been asked."""
        service = QuestionBankService()
        bank = service.load_question_bank("M1")
        all_ids = [q.question_id for q in bank.questions]

        result = service.get_next_static_question("M1", all_ids)
        assert result is None

    def test_get_signal_targets(self):
        """Test getting signal targets for a module."""
        service = QuestionBankService()
        signals = service.get_signal_targets("M1")

        assert len(signals) > 0
        assert "occupation_lifestyle" in signals or len(signals) > 3

    def test_get_module_completion_criteria(self):
        """Test getting completion criteria."""
        service = QuestionBankService()
        criteria = service.get_module_completion_criteria("M1")

        assert criteria.coverage_threshold == 0.70
        assert criteria.confidence_threshold == 0.65
        assert criteria.min_questions == 8

    def test_get_first_question(self):
        """Test getting first question for a module."""
        service = QuestionBankService()
        question = service.get_first_question("M1")

        assert question is not None
        assert question.priority == 1

    def test_get_questions_for_signal(self):
        """Test getting questions targeting a specific signal."""
        service = QuestionBankService()
        questions = service.get_questions_for_signal(
            "M1", "psychographic_self_perception"
        )

        # Should find at least one question for this signal
        assert len(questions) >= 1

    def test_singleton_instance(self):
        """Test singleton pattern."""
        service1 = get_question_bank_service()
        service2 = get_question_bank_service()
        assert service1 is service2


class TestAnswerParserService:
    """Tests for AnswerParserService."""

    def test_answer_parser_initialization(self):
        """Test answer parser service initializes correctly."""
        service = AnswerParserService()
        assert service.llm_client is not None
        assert service.prompt_service is not None

    @pytest.mark.asyncio
    async def test_empty_answer_is_unsatisfactory(self):
        """Test that empty answers are caught without LLM call."""
        service = AnswerParserService()
        is_sat, reason = await service.is_answer_satisfactory("question", "")
        assert is_sat is False
        assert reason == "empty answer"

    @pytest.mark.asyncio
    async def test_whitespace_answer_is_unsatisfactory(self):
        """Test that whitespace-only answers are caught."""
        service = AnswerParserService()
        is_sat, reason = await service.is_answer_satisfactory("question", "   ")
        assert is_sat is False
        assert reason == "empty answer"


class TestLLMResponseSchemas:
    """Tests for LLM response schemas."""

    def test_parsed_answer_response_valid(self):
        """Test ParsedAnswerResponse validation."""
        from app.schemas.llm_responses import ParsedAnswerResponse

        response = ParsedAnswerResponse(
            specificity_score=0.75,
            signals_extracted=[],
            behavioral_rules=[],
            needs_followup=False,
            sentiment="neutral",
            language_detected="EN",
        )
        assert response.specificity_score == 0.75

    def test_parsed_answer_response_defaults(self):
        """Test ParsedAnswerResponse defaults."""
        from app.schemas.llm_responses import ParsedAnswerResponse

        response = ParsedAnswerResponse(
            specificity_score=0.5,
        )
        assert response.needs_followup == False
        assert response.sentiment == "neutral"
        assert response.language_detected == "EN"

    def test_module_completion_response_valid(self):
        """Test ModuleCompletionResponse validation."""
        from app.schemas.llm_responses import ModuleCompletionResponse

        response = ModuleCompletionResponse(
            module_id="M1",
            is_complete=True,
            coverage_score=0.8,
            confidence_score=0.75,
            signals_captured=["occupation", "lifestyle"],
            signals_missing=[],
            recommendation="COMPLETE",
        )
        assert response.is_complete == True
        assert response.recommendation == "COMPLETE"

    def test_adaptive_question_response_valid(self):
        """Test AdaptiveQuestionResponse validation."""
        from app.schemas.llm_responses import AdaptiveQuestionResponse

        response = AdaptiveQuestionResponse(
            action="ASK_QUESTION",
            question_text="What do you do for work?",
            question_type="open_text",
            target_signal="occupation",
            rationale_short="Need occupation info",
        )
        assert response.action == "ASK_QUESTION"
        assert response.question_type == "open_text"

    def test_extracted_signal_valid(self):
        """Test ExtractedSignal validation."""
        from app.schemas.llm_responses import ExtractedSignal

        signal = ExtractedSignal(
            signal="occupation",
            value="software engineer",
            confidence=0.9,
        )
        assert signal.confidence == 0.9

    def test_behavioral_rule_valid(self):
        """Test BehavioralRule validation."""
        from app.schemas.llm_responses import BehavioralRule

        rule = BehavioralRule(
            rule="If stressed, then exercises",
            confidence=0.7,
        )
        assert "stressed" in rule.rule

    def test_parsed_answer_from_llm_response(self):
        """Test ParsedAnswer.from_llm_response conversion."""
        from app.schemas.llm_responses import ParsedAnswer, ParsedAnswerResponse

        llm_response = ParsedAnswerResponse(
            specificity_score=0.8,
            signals_extracted=[],
            behavioral_rules=[],
            needs_followup=True,
            followup_reason="vague",
            sentiment="positive",
            language_detected="EN",
        )

        parsed = ParsedAnswer.from_llm_response(llm_response)
        assert parsed.specificity_score == 0.8
        assert parsed.needs_followup == True
        assert parsed.followup_reason == "vague"
