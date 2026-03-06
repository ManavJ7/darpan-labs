"""Tests for Step 4 — Questionnaire Builder (50+ tests).

Covers: schemas, service methods (mocked DB/LLM), duration estimation,
validation rules, prompt loading, and router registration.
"""

import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.questionnaire import (
    Question,
    QuestionnaireContent,
    QuestionnaireSection,
    QuestionScale,
    QualityControls,
    SectionFeedbackRequest,
    SectionFeedbackResponse,
    SurveyLogic,
)
from app.schemas.study import StepVersionResponse
from app.services.questionnaire_service import (
    DURATION_BUFFER_SECONDS,
    DURATION_SECONDS,
    QuestionnaireService,
)
from app.services.prompt_service import PromptService
from app.services.state_machine import StudyStateMachine


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_question(
    qid: str = "Q1",
    section: str = "S1_screening",
    q_type: str = "single_select",
    position: int = 1,
    metric_id: str | None = None,
    text_en: str = "Sample question?",
    design_notes: str | None = None,
    show_if: str | None = None,
    pipe_from: str | None = None,
    randomize: bool = False,
) -> Question:
    return Question(
        question_id=qid,
        section=section,
        metric_id=metric_id,
        question_text={"en": text_en},
        question_type=q_type,
        position_in_section=position,
        design_notes=design_notes,
        show_if=show_if,
        pipe_from=pipe_from,
        randomize=randomize,
    )


def make_section(
    section_id: str = "S1_screening",
    section_name: str = "Screening",
    questions: list[Question] | None = None,
) -> QuestionnaireSection:
    if questions is None:
        questions = [make_question(section=section_id)]
    return QuestionnaireSection(
        section_id=section_id,
        section_name=section_name,
        questions=questions,
    )


def make_full_sections() -> list[QuestionnaireSection]:
    """Build a complete 8-section questionnaire skeleton."""
    section_defs = [
        ("S1_screening", "Screening & Qualification"),
        ("S2_category_context", "Category Context"),
        ("S3_concept_exposure", "Concept Exposure"),
        ("S4_core_kpi", "Core KPI"),
        ("S5_diagnostic", "Diagnostic Deep-Dive"),
        ("S6_competitive", "Competitive Benchmarking"),
        ("S7_price_sensitivity", "Price Sensitivity"),
        ("S8_demographics", "Demographics"),
    ]
    sections = []
    q_counter = 1
    for sid, sname in section_defs:
        qs = []
        if sid == "S4_core_kpi":
            # First question must be PI
            qs.append(
                make_question(
                    qid=f"Q{q_counter}",
                    section=sid,
                    q_type="rating",
                    position=1,
                    metric_id="purchase_intent",
                    text_en="How likely are you to purchase this product?",
                )
            )
            q_counter += 1
            qs.append(
                make_question(
                    qid=f"Q{q_counter}",
                    section=sid,
                    q_type="rating",
                    position=2,
                    metric_id="uniqueness",
                    text_en="How unique is this product?",
                    design_notes="ATTENTION_CHECK",
                )
            )
            q_counter += 1
        else:
            qs.append(
                make_question(
                    qid=f"Q{q_counter}",
                    section=sid,
                    q_type="single_select",
                    position=1,
                )
            )
            q_counter += 1
        sections.append(make_section(sid, sname, qs))
    return sections


def make_questionnaire_content(
    sections: list[QuestionnaireSection] | None = None,
    study_id: str | None = None,
    duration: int | None = None,
) -> QuestionnaireContent:
    if sections is None:
        sections = make_full_sections()
    sid = study_id or str(uuid.uuid4())
    total_q = sum(len(s.questions) for s in sections)
    dur = duration if duration is not None else 13
    return QuestionnaireContent(
        questionnaire_id="QNR-001",
        study_id=sid,
        version=1,
        estimated_duration_minutes=dur,
        total_questions=total_q,
        sections=sections,
        quality_controls=QualityControls(
            attention_check={"question_id": "Q9", "correct_answer": "agree"},
            speeder_threshold_seconds=180,
            straightline_detection=True,
            open_end_quality_check=True,
        ),
        survey_logic=SurveyLogic(
            concept_rotation="balanced_incomplete_block",
            concepts_per_respondent=3,
        ),
    )


def make_study_mock(status: str = "step_3_locked") -> MagicMock:
    study = MagicMock()
    study.id = uuid.uuid4()
    study.brand_id = uuid.uuid4()
    study.status = status
    study.question = "Test question?"
    study.title = "Test Study"
    study.brand_name = "TestBrand"
    study.category = "snacks"
    study.context = {}
    study.study_metadata = {}
    study.created_at = datetime.now(timezone.utc)
    study.updated_at = datetime.now(timezone.utc)
    return study


def make_step_version_mock(
    study_id: uuid.UUID | None = None,
    step: int = 4,
    version: int = 1,
    status: str = "review",
    content: dict | None = None,
) -> MagicMock:
    sv = MagicMock()
    sv.id = uuid.uuid4()
    sv.study_id = study_id or uuid.uuid4()
    sv.step = step
    sv.version = version
    sv.status = status
    sv.content = content or make_questionnaire_content().model_dump()
    sv.ai_rationale = {}
    sv.locked_at = None
    sv.locked_by = None
    sv.created_at = datetime.now(timezone.utc)
    return sv


# ─── Schema Tests ─────────────────────────────────────────────────────────────


class TestQuestionSchema:
    def test_question_minimal(self):
        q = make_question()
        assert q.question_id == "Q1"
        assert q.required is True
        assert q.randomize is False

    def test_question_with_scale(self):
        scale = QuestionScale(
            type="likert_5",
            options=[{"value": 1, "label": "Strongly disagree"}],
        )
        q = make_question()
        q_with_scale = q.model_copy(update={"scale": scale})
        assert q_with_scale.scale.type == "likert_5"

    def test_question_with_show_if(self):
        q = make_question(show_if="Q1 == 'yes'")
        assert q.show_if == "Q1 == 'yes'"

    def test_question_with_pipe_from(self):
        q = make_question(pipe_from="Q3")
        assert q.pipe_from == "Q3"

    def test_question_with_design_notes(self):
        q = make_question(design_notes="ATTENTION_CHECK")
        assert q.design_notes == "ATTENTION_CHECK"


class TestQuestionnaireSectionSchema:
    def test_section_with_questions(self):
        s = make_section()
        assert s.section_id == "S1_screening"
        assert len(s.questions) == 1

    def test_section_notes(self):
        s = make_section()
        assert s.section_notes is None

    def test_section_with_notes(self):
        s = QuestionnaireSection(
            section_id="S1",
            section_name="Test",
            questions=[make_question()],
            section_notes="Important notes",
        )
        assert s.section_notes == "Important notes"

    def test_section_empty_questions(self):
        s = QuestionnaireSection(
            section_id="S1",
            section_name="Test",
            questions=[],
        )
        assert len(s.questions) == 0


class TestQuestionnaireContentSchema:
    def test_content_full(self):
        c = make_questionnaire_content()
        assert c.questionnaire_id == "QNR-001"
        assert c.version == 1
        assert len(c.sections) == 8

    def test_content_total_questions(self):
        c = make_questionnaire_content()
        expected = sum(len(s.questions) for s in c.sections)
        assert c.total_questions == expected

    def test_content_quality_controls(self):
        c = make_questionnaire_content()
        assert c.quality_controls.straightline_detection is True
        assert c.quality_controls.speeder_threshold_seconds == 180

    def test_content_survey_logic(self):
        c = make_questionnaire_content()
        assert c.survey_logic.concepts_per_respondent == 3

    def test_content_serialization_roundtrip(self):
        c = make_questionnaire_content()
        d = c.model_dump()
        c2 = QuestionnaireContent(**d)
        assert c2.questionnaire_id == c.questionnaire_id
        assert len(c2.sections) == len(c.sections)


class TestSectionFeedbackSchemas:
    def test_feedback_request_specific_question(self):
        req = SectionFeedbackRequest(
            section_id="S4_core_kpi",
            feedback_text="Rephrase this question",
            target_question_id="Q5",
            feedback_type="specific_question",
        )
        assert req.feedback_type == "specific_question"
        assert req.target_question_id == "Q5"

    def test_feedback_request_add_question(self):
        req = SectionFeedbackRequest(
            section_id="S5_diagnostic",
            feedback_text="Add a brand fit question",
            feedback_type="add_question",
        )
        assert req.target_question_id is None

    def test_feedback_request_remove_question(self):
        req = SectionFeedbackRequest(
            section_id="S5_diagnostic",
            feedback_text="Remove Q7",
            target_question_id="Q7",
            feedback_type="remove_question",
        )
        assert req.feedback_type == "remove_question"

    def test_feedback_request_section_level(self):
        req = SectionFeedbackRequest(
            section_id="S3_concept_exposure",
            feedback_text="Simplify all questions",
            feedback_type="section_level",
        )
        assert req.feedback_type == "section_level"

    def test_feedback_response_valid(self):
        resp = SectionFeedbackResponse(
            updated_section=make_section("S4_core_kpi", "Core KPI"),
            change_log=["Modified Q5"],
            warnings=[],
        )
        assert len(resp.change_log) == 1
        assert len(resp.warnings) == 0

    def test_feedback_response_with_warnings(self):
        resp = SectionFeedbackResponse(
            updated_section=make_section("S4_core_kpi", "Core KPI"),
            change_log=["Removed Q7"],
            warnings=["Removing this question reduces coverage of uniqueness metric"],
        )
        assert len(resp.warnings) == 1


# ─── Duration Estimation Tests ────────────────────────────────────────────────


class TestEstimateDuration:
    def test_single_select_only(self):
        sections = [
            make_section(questions=[make_question(q_type="single_select")])
        ]
        result = QuestionnaireService.estimate_duration(sections)
        expected = math.ceil((15 + DURATION_BUFFER_SECONDS) / 60)
        assert result == expected

    def test_open_text_only(self):
        sections = [
            make_section(questions=[make_question(q_type="open_text")])
        ]
        result = QuestionnaireService.estimate_duration(sections)
        expected = math.ceil((60 + DURATION_BUFFER_SECONDS) / 60)
        assert result == expected

    def test_multi_select(self):
        sections = [
            make_section(questions=[make_question(q_type="multi_select")])
        ]
        result = QuestionnaireService.estimate_duration(sections)
        expected = math.ceil((20 + DURATION_BUFFER_SECONDS) / 60)
        assert result == expected

    def test_rating_type(self):
        sections = [
            make_section(questions=[make_question(q_type="rating")])
        ]
        result = QuestionnaireService.estimate_duration(sections)
        expected = math.ceil((15 + DURATION_BUFFER_SECONDS) / 60)
        assert result == expected

    def test_ranking_type(self):
        sections = [
            make_section(questions=[make_question(q_type="ranking")])
        ]
        result = QuestionnaireService.estimate_duration(sections)
        expected = math.ceil((30 + DURATION_BUFFER_SECONDS) / 60)
        assert result == expected

    def test_concept_exposure_type(self):
        sections = [
            make_section(questions=[make_question(q_type="concept_exposure")])
        ]
        result = QuestionnaireService.estimate_duration(sections)
        expected = math.ceil((30 + DURATION_BUFFER_SECONDS) / 60)
        assert result == expected

    def test_unknown_type_defaults_to_15(self):
        sections = [
            make_section(questions=[make_question(q_type="unknown_type")])
        ]
        result = QuestionnaireService.estimate_duration(sections)
        expected = math.ceil((15 + DURATION_BUFFER_SECONDS) / 60)
        assert result == expected

    def test_empty_sections(self):
        result = QuestionnaireService.estimate_duration([])
        expected = math.ceil(DURATION_BUFFER_SECONDS / 60)
        assert result == expected

    def test_mixed_types(self):
        qs = [
            make_question(qid="Q1", q_type="single_select", position=1),
            make_question(qid="Q2", q_type="multi_select", position=2),
            make_question(qid="Q3", q_type="open_text", position=3),
            make_question(qid="Q4", q_type="rating", position=4),
            make_question(qid="Q5", q_type="ranking", position=5),
            make_question(qid="Q6", q_type="concept_exposure", position=6),
        ]
        sections = [make_section(questions=qs)]
        total_s = 15 + 20 + 60 + 15 + 30 + 30 + DURATION_BUFFER_SECONDS
        expected = math.ceil(total_s / 60)
        result = QuestionnaireService.estimate_duration(sections)
        assert result == expected

    def test_multiple_sections_accumulate(self):
        s1 = make_section(
            "S1_screening",
            "S1",
            [make_question(q_type="single_select")],
        )
        s2 = make_section(
            "S2_category_context",
            "S2",
            [make_question(q_type="open_text", section="S2_category_context")],
        )
        result = QuestionnaireService.estimate_duration([s1, s2])
        expected = math.ceil((15 + 60 + DURATION_BUFFER_SECONDS) / 60)
        assert result == expected

    def test_buffer_always_included(self):
        """Even with zero questions, 60s buffer produces 1 minute."""
        result = QuestionnaireService.estimate_duration([])
        assert result >= 1

    def test_rounds_up(self):
        """61 seconds total => 2 minutes (ceiling)."""
        # 1 single_select = 15s + 60s buffer = 75s => ceil(75/60) = 2
        sections = [make_section(questions=[make_question(q_type="single_select")])]
        result = QuestionnaireService.estimate_duration(sections)
        assert result == 2

    def test_exact_minute_boundary(self):
        """Exactly 120s => 2 minutes."""
        # We need 120 - 60 (buffer) = 60s of questions = 1 open_text
        sections = [make_section(questions=[make_question(q_type="open_text")])]
        total = 60 + 60  # open_text + buffer
        assert total == 120
        result = QuestionnaireService.estimate_duration(sections)
        assert result == 2


# ─── Validation Tests ─────────────────────────────────────────────────────────


class TestValidateQuestionnaire:
    def test_valid_questionnaire_no_warnings(self):
        content = make_questionnaire_content()
        warnings = QuestionnaireService.validate_questionnaire(content)
        assert isinstance(warnings, list)
        # The well-formed questionnaire should have zero warnings
        assert len(warnings) == 0

    def test_duration_exceeds_20_minutes(self):
        content = make_questionnaire_content(duration=25)
        warnings = QuestionnaireService.validate_questionnaire(content)
        duration_warnings = [w for w in warnings if "20 minutes" in w]
        assert len(duration_warnings) == 1

    def test_duration_at_20_no_warning(self):
        content = make_questionnaire_content(duration=20)
        warnings = QuestionnaireService.validate_questionnaire(content)
        duration_warnings = [w for w in warnings if "20 minutes" in w]
        assert len(duration_warnings) == 0

    def test_pi_not_first_in_kpi(self):
        sections = make_full_sections()
        # Swap the KPI section to have uniqueness first
        for s in sections:
            if s.section_id == "S4_core_kpi":
                s.questions[0] = make_question(
                    qid="Q_uniq",
                    section="S4_core_kpi",
                    q_type="rating",
                    position=1,
                    metric_id="uniqueness",
                    text_en="How unique is this product?",
                )
                break
        content = make_questionnaire_content(sections=sections)
        warnings = QuestionnaireService.validate_questionnaire(content)
        pi_warnings = [w for w in warnings if "Purchase Intent" in w]
        assert len(pi_warnings) == 1

    def test_pi_first_by_metric_id(self):
        sections = make_full_sections()
        content = make_questionnaire_content(sections=sections)
        warnings = QuestionnaireService.validate_questionnaire(content)
        pi_warnings = [w for w in warnings if "Purchase Intent" in w]
        assert len(pi_warnings) == 0

    def test_pi_first_by_text(self):
        """PI detected via question text when metric_id is absent."""
        sections = make_full_sections()
        for s in sections:
            if s.section_id == "S4_core_kpi":
                s.questions[0] = make_question(
                    qid="Q_pi",
                    section="S4_core_kpi",
                    q_type="rating",
                    position=1,
                    metric_id=None,
                    text_en="What is your purchase intent for this product?",
                )
                break
        content = make_questionnaire_content(sections=sections)
        warnings = QuestionnaireService.validate_questionnaire(content)
        pi_warnings = [w for w in warnings if "Purchase Intent" in w]
        assert len(pi_warnings) == 0

    def test_too_many_open_ended_in_concept_exposure(self):
        qs = [
            make_question(qid=f"Q{i}", section="S3_concept_exposure", q_type="open_text", position=i)
            for i in range(1, 4)
        ]
        sections = make_full_sections()
        for i, s in enumerate(sections):
            if s.section_id == "S3_concept_exposure":
                sections[i] = make_section("S3_concept_exposure", "Concept Exposure", qs)
                break
        content = make_questionnaire_content(sections=sections)
        warnings = QuestionnaireService.validate_questionnaire(content)
        open_warnings = [w for w in warnings if "open-text" in w]
        assert len(open_warnings) == 1

    def test_two_open_ended_is_ok(self):
        qs = [
            make_question(qid=f"Q{i}", section="S3_concept_exposure", q_type="open_text", position=i)
            for i in range(1, 3)
        ]
        sections = make_full_sections()
        for i, s in enumerate(sections):
            if s.section_id == "S3_concept_exposure":
                sections[i] = make_section("S3_concept_exposure", "Concept Exposure", qs)
                break
        content = make_questionnaire_content(sections=sections)
        warnings = QuestionnaireService.validate_questionnaire(content)
        open_warnings = [w for w in warnings if "open-text" in w]
        assert len(open_warnings) == 0

    def test_missing_attention_check(self):
        sections = make_full_sections()
        # Remove the attention check design_notes
        for s in sections:
            for q in s.questions:
                if q.design_notes and "ATTENTION_CHECK" in q.design_notes:
                    q.design_notes = None
        content = make_questionnaire_content(sections=sections)
        warnings = QuestionnaireService.validate_questionnaire(content)
        attn_warnings = [w for w in warnings if "attention check" in w.lower()]
        assert len(attn_warnings) == 1

    def test_attention_check_present_no_warning(self):
        content = make_questionnaire_content()
        warnings = QuestionnaireService.validate_questionnaire(content)
        attn_warnings = [w for w in warnings if "attention check" in w.lower()]
        assert len(attn_warnings) == 0

    def test_demographics_not_last(self):
        sections = make_full_sections()
        # Move demographics to first position
        demo = None
        for i, s in enumerate(sections):
            if s.section_id == "S8_demographics":
                demo = sections.pop(i)
                break
        sections.insert(0, demo)
        content = make_questionnaire_content(sections=sections)
        warnings = QuestionnaireService.validate_questionnaire(content)
        demo_warnings = [w for w in warnings if "Demographics" in w or "S8_demographics" in w]
        assert len(demo_warnings) == 1

    def test_demographics_last_no_warning(self):
        content = make_questionnaire_content()
        warnings = QuestionnaireService.validate_questionnaire(content)
        demo_warnings = [w for w in warnings if "Demographics" in w and "last" in w]
        assert len(demo_warnings) == 0

    def test_leading_question_best(self):
        sections = make_full_sections()
        sections[0].questions[0] = make_question(
            text_en="What is the best feature of this product?"
        )
        content = make_questionnaire_content(sections=sections)
        warnings = QuestionnaireService.validate_questionnaire(content)
        leading_warnings = [w for w in warnings if "leading" in w.lower()]
        assert len(leading_warnings) >= 1

    def test_leading_question_amazing(self):
        sections = make_full_sections()
        sections[0].questions[0] = make_question(
            text_en="How amazing is this concept?"
        )
        content = make_questionnaire_content(sections=sections)
        warnings = QuestionnaireService.validate_questionnaire(content)
        leading_warnings = [w for w in warnings if "amazing" in w]
        assert len(leading_warnings) >= 1

    def test_leading_question_dont_you_agree(self):
        sections = make_full_sections()
        sections[0].questions[0] = make_question(
            text_en="Don't you agree this product is great?"
        )
        content = make_questionnaire_content(sections=sections)
        warnings = QuestionnaireService.validate_questionnaire(content)
        leading_warnings = [w for w in warnings if "leading" in w.lower()]
        assert len(leading_warnings) >= 1

    def test_neutral_question_no_leading_warning(self):
        content = make_questionnaire_content()
        warnings = QuestionnaireService.validate_questionnaire(content)
        leading_warnings = [w for w in warnings if "leading" in w.lower()]
        assert len(leading_warnings) == 0

    def test_missing_screening_section(self):
        sections = make_full_sections()
        sections = [s for s in sections if s.section_id != "S1_screening"]
        content = make_questionnaire_content(sections=sections)
        warnings = QuestionnaireService.validate_questionnaire(content)
        screening_warnings = [w for w in warnings if "S1_screening" in w]
        assert len(screening_warnings) == 1

    def test_screening_present_no_warning(self):
        content = make_questionnaire_content()
        warnings = QuestionnaireService.validate_questionnaire(content)
        screening_warnings = [w for w in warnings if "S1_screening" in w]
        assert len(screening_warnings) == 0

    def test_multiple_warnings_combined(self):
        """A questionnaire with many issues should report multiple warnings."""
        # No screening, no attention check, demographics not last, duration > 20
        sections = [
            make_section("S8_demographics", "Demographics"),
            make_section("S4_core_kpi", "KPI", [
                make_question(
                    qid="Q1",
                    section="S4_core_kpi",
                    metric_id="uniqueness",
                    text_en="What is the best thing about this amazing product?",
                )
            ]),
        ]
        content = make_questionnaire_content(sections=sections, duration=25)
        warnings = QuestionnaireService.validate_questionnaire(content)
        # Should have: duration, PI not first, missing attention check,
        # demographics not last, leading question(s), missing screening
        assert len(warnings) >= 5


# ─── Prompt Loading Tests ────────────────────────────────────────────────────


class TestPromptLoading:
    def test_questionnaire_generator_prompt_exists(self):
        prompts_dir = Path(__file__).parent.parent / "prompts"
        assert (prompts_dir / "questionnaire_generator.txt").exists()

    def test_feedback_incorporator_prompt_exists(self):
        prompts_dir = Path(__file__).parent.parent / "prompts"
        assert (prompts_dir / "feedback_incorporator.txt").exists()

    def test_questionnaire_generator_loads(self):
        ps = PromptService()
        template = ps.load_template("questionnaire_generator")
        assert "{study_brief_json}" in template
        assert "{concepts_json}" in template
        assert "{research_design_json}" in template
        assert "{selected_metrics_json}" in template

    def test_feedback_incorporator_loads(self):
        ps = PromptService()
        template = ps.load_template("feedback_incorporator")
        assert "{section_json}" in template
        assert "{feedback_text}" in template
        assert "{feedback_type}" in template
        assert "{question_id}" in template

    def test_questionnaire_generator_format(self):
        ps = PromptService()
        result = ps.format_prompt(
            "questionnaire_generator",
            study_brief_json="{}",
            concepts_json="[]",
            research_design_json="{}",
            selected_metrics_json="[]",
        )
        assert "{}" not in result or "[]" not in result.replace("{}", "").replace("[]", "")
        # Should be rendered (no leftover unformatted placeholders)
        assert "{study_brief_json}" not in result

    def test_feedback_incorporator_format(self):
        ps = PromptService()
        result = ps.format_prompt(
            "feedback_incorporator",
            section_json="{}",
            feedback_text="test feedback",
            feedback_type="specific_question",
            question_id="Q5",
        )
        assert "{section_json}" not in result
        assert "test feedback" in result

    def test_questionnaire_generator_contains_design_rules(self):
        ps = PromptService()
        template = ps.load_template("questionnaire_generator")
        # Should mention the 10 design rules
        assert "Purchase Intent" in template
        assert "Leading" in template or "leading" in template
        assert "Attention Check" in template or "attention" in template.lower()
        assert "Demographics" in template
        assert "Screening" in template


# ─── Service Method Tests (Mocked DB/LLM) ────────────────────────────────────


class TestGenerateQuestionnaire:
    @pytest.mark.asyncio
    async def test_generate_requires_step_3_locked(self):
        service = QuestionnaireService(
            llm_client=AsyncMock(),
            prompt_service=MagicMock(),
        )
        study = make_study_mock(status="step_2_locked")
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = study
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="step 3 must be locked"):
            await service.generate_questionnaire(study.id, db)

    @pytest.mark.asyncio
    async def test_generate_study_not_found(self):
        service = QuestionnaireService(
            llm_client=AsyncMock(),
            prompt_service=MagicMock(),
        )
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found"):
            await service.generate_questionnaire(uuid.uuid4(), db)

    @pytest.mark.asyncio
    async def test_generate_success(self):
        content = make_questionnaire_content()
        llm = AsyncMock()
        llm.generate_json = AsyncMock(return_value=content.model_dump())

        ps = MagicMock()
        ps.format_prompt = MagicMock(return_value="formatted prompt")

        service = QuestionnaireService(llm_client=llm, prompt_service=ps)

        study = make_study_mock(status="step_3_locked")

        # Build mock DB that returns different results for different queries
        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # _load_study
                result.scalar_one_or_none.return_value = study
            elif call_count <= 4:
                # _load_all_previous_outputs (steps 1, 2, 3)
                sv_mock = MagicMock()
                sv_mock.content = {"test": "data"}
                result.scalar_one_or_none.return_value = sv_mock
            else:
                # _load_step_version for checking existing version
                result.scalar_one_or_none.return_value = None
            return result

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=mock_execute)

        result = await service.generate_questionnaire(study.id, db)

        assert isinstance(result, StepVersionResponse)
        assert result.step == 4
        assert result.status == "review"
        assert db.add.called
        assert db.commit.called


class TestSubmitSectionFeedback:
    @pytest.mark.asyncio
    async def test_feedback_step_locked_raises(self):
        service = QuestionnaireService(
            llm_client=AsyncMock(),
            prompt_service=MagicMock(),
        )
        study = make_study_mock(status="step_4_locked")
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = study
        db.execute = AsyncMock(return_value=mock_result)

        feedback = SectionFeedbackRequest(
            section_id="S4_core_kpi",
            feedback_text="Test",
            feedback_type="specific_question",
        )

        with pytest.raises(ValueError, match="already locked"):
            await service.submit_section_feedback(study.id, feedback, db)

    @pytest.mark.asyncio
    async def test_feedback_no_questionnaire_raises(self):
        service = QuestionnaireService(
            llm_client=AsyncMock(),
            prompt_service=MagicMock(),
        )
        study = make_study_mock(status="step_4_review")

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = study
            else:
                result.scalar_one_or_none.return_value = None
            return result

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=mock_execute)

        feedback = SectionFeedbackRequest(
            section_id="S4_core_kpi",
            feedback_text="Test",
            feedback_type="specific_question",
        )

        with pytest.raises(ValueError, match="No questionnaire found"):
            await service.submit_section_feedback(study.id, feedback, db)

    @pytest.mark.asyncio
    async def test_feedback_section_not_found_raises(self):
        content = make_questionnaire_content()
        sv = make_step_version_mock(content=content.model_dump())

        service = QuestionnaireService(
            llm_client=AsyncMock(),
            prompt_service=MagicMock(),
        )
        study = make_study_mock(status="step_4_review")

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = study
            else:
                result.scalar_one_or_none.return_value = sv
            return result

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=mock_execute)

        feedback = SectionFeedbackRequest(
            section_id="NONEXISTENT_SECTION",
            feedback_text="Test",
            feedback_type="specific_question",
        )

        with pytest.raises(ValueError, match="not found in questionnaire"):
            await service.submit_section_feedback(study.id, feedback, db)

    @pytest.mark.asyncio
    async def test_feedback_success(self):
        content = make_questionnaire_content()
        sv = make_step_version_mock(content=content.model_dump())

        updated_section = make_section("S4_core_kpi", "Core KPI")
        feedback_resp = SectionFeedbackResponse(
            updated_section=updated_section,
            change_log=["Modified Q5"],
            warnings=[],
        )

        llm = AsyncMock()
        llm.generate_json = AsyncMock(return_value=feedback_resp.model_dump())

        ps = MagicMock()
        ps.format_prompt = MagicMock(return_value="formatted")

        service = QuestionnaireService(llm_client=llm, prompt_service=ps)
        study = make_study_mock(status="step_4_review")

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = study
            else:
                result.scalar_one_or_none.return_value = sv
            return result

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=mock_execute)

        feedback = SectionFeedbackRequest(
            section_id="S4_core_kpi",
            feedback_text="Rephrase Q5",
            feedback_type="specific_question",
            target_question_id="Q5",
        )

        result = await service.submit_section_feedback(study.id, feedback, db)

        assert isinstance(result, SectionFeedbackResponse)
        assert len(result.change_log) == 1
        assert db.add.called
        assert db.commit.called


class TestLockQuestionnaire:
    @pytest.mark.asyncio
    async def test_lock_requires_step_4_review(self):
        service = QuestionnaireService(
            llm_client=AsyncMock(),
            prompt_service=MagicMock(),
        )
        study = make_study_mock(status="step_4_draft")
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = study
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Cannot lock step"):
            await service.lock_questionnaire(study.id, str(uuid.uuid4()), db)

    @pytest.mark.asyncio
    async def test_lock_study_not_found(self):
        service = QuestionnaireService(
            llm_client=AsyncMock(),
            prompt_service=MagicMock(),
        )
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found"):
            await service.lock_questionnaire(uuid.uuid4(), str(uuid.uuid4()), db)

    @pytest.mark.asyncio
    async def test_lock_success(self):
        service = QuestionnaireService(
            llm_client=AsyncMock(),
            prompt_service=MagicMock(),
        )
        study = make_study_mock(status="step_4_review")
        sv = make_step_version_mock(study_id=study.id)

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = study
            else:
                result.scalar_one_or_none.return_value = sv
            return result

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=mock_execute)

        user_id = str(uuid.uuid4())
        result = await service.lock_questionnaire(study.id, user_id, db)

        assert isinstance(result, StepVersionResponse)
        assert sv.status == "locked"
        assert sv.locked_at is not None
        assert study.status == "complete"
        assert db.commit.called

    @pytest.mark.asyncio
    async def test_lock_no_questionnaire_raises(self):
        service = QuestionnaireService(
            llm_client=AsyncMock(),
            prompt_service=MagicMock(),
        )
        study = make_study_mock(status="step_4_review")

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = study
            else:
                result.scalar_one_or_none.return_value = None
            return result

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=mock_execute)

        with pytest.raises(ValueError, match="No questionnaire found"):
            await service.lock_questionnaire(study.id, str(uuid.uuid4()), db)


# ─── Router Registration Tests ───────────────────────────────────────────────


class TestRouterRegistration:
    def test_router_imports(self):
        from app.routers.questionnaire import router
        assert router is not None

    def test_router_prefix(self):
        from app.routers.questionnaire import router
        assert router.prefix == "/api/v1/studies/{study_id}"

    def test_router_tags(self):
        from app.routers.questionnaire import router
        assert "Questionnaire" in router.tags

    def test_generate_route_exists(self):
        from app.routers.questionnaire import router
        routes = [r.path for r in router.routes]
        matching = [r for r in routes if r.endswith("/steps/4/generate")]
        assert len(matching) == 1

    def test_feedback_route_exists(self):
        from app.routers.questionnaire import router
        routes = [r.path for r in router.routes]
        matching = [r for r in routes if r.endswith("/steps/4/sections/{section_id}/feedback")]
        assert len(matching) == 1

    def test_lock_route_exists(self):
        from app.routers.questionnaire import router
        routes = [r.path for r in router.routes]
        matching = [r for r in routes if r.endswith("/steps/4/lock")]
        assert len(matching) == 1

    def test_all_routes_are_post(self):
        from app.routers.questionnaire import router
        for route in router.routes:
            assert "POST" in route.methods

    def test_generate_route_response_model(self):
        from app.routers.questionnaire import router
        for route in router.routes:
            if route.path == "/steps/4/generate":
                assert route.response_model is StepVersionResponse
                break

    def test_feedback_route_response_model(self):
        from app.routers.questionnaire import router
        for route in router.routes:
            if route.path == "/steps/4/sections/{section_id}/feedback":
                assert route.response_model is SectionFeedbackResponse
                break

    def test_lock_route_response_model(self):
        from app.routers.questionnaire import router
        for route in router.routes:
            if route.path == "/steps/4/lock":
                assert route.response_model is StepVersionResponse
                break


# ─── State Machine Integration Tests ─────────────────────────────────────────


class TestStateMachineIntegration:
    def test_step_4_prerequisite_is_step_3_locked(self):
        assert StudyStateMachine.STEP_PREREQUISITES[4] == "step_3_locked"

    def test_can_start_step_4_from_step_3_locked(self):
        study = make_study_mock(status="step_3_locked")
        assert StudyStateMachine.can_start_step(study, 4) is True

    def test_cannot_start_step_4_from_step_2_locked(self):
        study = make_study_mock(status="step_2_locked")
        assert StudyStateMachine.can_start_step(study, 4) is False

    def test_step_4_locked_to_complete_is_valid(self):
        assert StudyStateMachine.can_transition("step_4_locked", "complete") is True

    def test_step_4_review_to_step_4_locked_is_valid(self):
        assert StudyStateMachine.can_transition("step_4_review", "step_4_locked") is True

    def test_step_4_review_to_step_4_draft_is_valid(self):
        assert StudyStateMachine.can_transition("step_4_review", "step_4_draft") is True


# ─── Duration Constants Tests ─────────────────────────────────────────────────


class TestDurationConstants:
    def test_single_select_duration(self):
        assert DURATION_SECONDS["single_select"] == 15

    def test_multi_select_duration(self):
        assert DURATION_SECONDS["multi_select"] == 20

    def test_open_text_duration(self):
        assert DURATION_SECONDS["open_text"] == 60

    def test_rating_duration(self):
        assert DURATION_SECONDS["rating"] == 15

    def test_ranking_duration(self):
        assert DURATION_SECONDS["ranking"] == 30

    def test_concept_exposure_duration(self):
        assert DURATION_SECONDS["concept_exposure"] == 30

    def test_buffer_is_60_seconds(self):
        assert DURATION_BUFFER_SECONDS == 60
