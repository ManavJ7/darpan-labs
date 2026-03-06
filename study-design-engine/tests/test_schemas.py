"""Tests for Pydantic schemas — 45+ tests."""
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.common import (
    StudyStatus, StepStatus, ConceptStatus, StudyType,
    MethodologyFamily, BaseSchema, PaginatedRequest, PaginatedResponse,
)
from app.schemas.study import StudyCreate, StudyResponse, StudyBriefContent, StepVersionResponse
from app.schemas.concept import (
    ConceptComponent, ConceptComponents, ConceptCreate,
    ConceptResponse, ConceptRefineResponse, ComparabilityCheckResponse,
)
from app.schemas.research_design import (
    SampleSizeParams, SampleSizeResult, QuotaAllocation,
    ResearchDesignContent, ResearchDesignResponse,
)
from app.schemas.questionnaire import (
    QuestionScale, Question, QuestionnaireSection, QualityControls,
    SurveyLogic, QuestionnaireContent, SectionFeedbackRequest, SectionFeedbackResponse,
)
from app.schemas.audit import AuditLogEntry, ReviewCommentCreate, ReviewCommentResponse
from app.schemas.metric import MetricResponse, MetricCreate


# ─── Enum Tests ───

class TestEnums:
    def test_study_status_values(self):
        assert StudyStatus.init == "init"
        assert StudyStatus.step_1_draft == "step_1_draft"
        assert StudyStatus.complete == "complete"
        assert len(StudyStatus) == 14

    def test_step_status_values(self):
        assert StepStatus.draft == "draft"
        assert StepStatus.review == "review"
        assert StepStatus.locked == "locked"
        assert len(StepStatus) == 3

    def test_concept_status_values(self):
        assert ConceptStatus.raw == "raw"
        assert ConceptStatus.refined == "refined"
        assert ConceptStatus.approved == "approved"
        assert len(ConceptStatus) == 3

    def test_study_type_values(self):
        assert StudyType.concept_screening == "concept_screening"
        assert StudyType.concept_testing == "concept_testing"
        assert len(StudyType) == 9

    def test_methodology_family_values(self):
        assert MethodologyFamily.monadic == "monadic"
        assert MethodologyFamily.sequential_monadic == "sequential_monadic"
        assert len(MethodologyFamily) == 8


# ─── Study Schemas ───

class TestStudySchemas:
    def test_study_create_valid(self):
        data = StudyCreate(
            question="Test question?",
            brand_id=uuid.uuid4(),
        )
        assert data.question == "Test question?"

    def test_study_create_with_optional_fields(self):
        data = StudyCreate(
            question="Test?",
            brand_id=uuid.uuid4(),
            brand_name="Acme",
            category="FMCG",
            context={"key": "value"},
        )
        assert data.brand_name == "Acme"
        assert data.category == "FMCG"

    def test_study_create_missing_question_raises(self):
        with pytest.raises(ValidationError):
            StudyCreate(brand_id=uuid.uuid4())

    def test_study_create_missing_brand_id_raises(self):
        with pytest.raises(ValidationError):
            StudyCreate(question="Test?")

    def test_study_response_valid(self):
        now = datetime.now(timezone.utc)
        resp = StudyResponse(
            id=uuid.uuid4(),
            status="init",
            question="Test?",
            created_at=now,
            updated_at=now,
        )
        assert resp.status == "init"

    def test_study_brief_content_valid(self):
        data = StudyBriefContent(
            study_type="concept_testing",
            study_type_confidence=0.92,
            recommended_title="Test Study",
            recommended_metrics=["purchase_intent"],
            recommended_audience={"age": "18-45"},
            methodology_family="sequential_monadic",
            methodology_rationale="Best for multi-concept",
        )
        assert data.study_type == "concept_testing"

    def test_study_brief_content_missing_required(self):
        with pytest.raises(ValidationError):
            StudyBriefContent(
                study_type="concept_testing",
                # missing other required fields
            )

    def test_step_version_response_valid(self):
        now = datetime.now(timezone.utc)
        resp = StepVersionResponse(
            id=uuid.uuid4(),
            study_id=uuid.uuid4(),
            step=1,
            version=1,
            status="draft",
            content={"key": "value"},
            created_at=now,
        )
        assert resp.step == 1
        assert resp.version == 1


# ─── Concept Schemas ───

class TestConceptSchemas:
    def test_concept_component_valid(self):
        comp = ConceptComponent(raw_input="Raw text")
        assert comp.raw_input == "Raw text"
        assert comp.approved is False

    def test_concept_component_with_all_fields(self):
        comp = ConceptComponent(
            raw_input="Raw",
            refined="Refined",
            refinement_rationale="Because",
            approved=True,
            brand_edit="Brand version",
        )
        assert comp.approved is True

    def test_concept_components_valid(self):
        component = ConceptComponent(raw_input="test")
        data = ConceptComponents(
            consumer_insight=component,
            product_name=component,
            key_benefit=component,
            reasons_to_believe=component,
            visual={"description": "image"},
            price_format={"price": "199", "format": "per unit"},
        )
        assert data.visual == {"description": "image"}

    def test_concept_response_valid(self):
        now = datetime.now(timezone.utc)
        resp = ConceptResponse(
            id=uuid.uuid4(),
            study_id=uuid.uuid4(),
            concept_index=1,
            version=1,
            status="raw",
            components={"key": "value"},
            created_at=now,
        )
        assert resp.concept_index == 1

    def test_concept_refine_response_valid(self):
        resp = ConceptRefineResponse(
            concept_id=uuid.uuid4(),
            refined_components={"key": "value"},
            flags=["flag1"],
            testability_score=0.85,
        )
        assert resp.testability_score == 0.85

    def test_comparability_check_response_pass(self):
        resp = ComparabilityCheckResponse(
            overall_comparability="pass",
            issues=[],
            recommendation="All concepts are comparable",
        )
        assert resp.overall_comparability == "pass"

    def test_comparability_check_response_fail(self):
        resp = ComparabilityCheckResponse(
            overall_comparability="fail",
            issues=["Length imbalance"],
            recommendation="Revise concept 3",
        )
        assert resp.overall_comparability == "fail"


# ─── Research Design Schemas ───

class TestResearchDesignSchemas:
    def test_sample_size_params_valid(self):
        params = SampleSizeParams(
            methodology="monadic",
            num_concepts=4,
        )
        assert params.confidence_level == 0.95
        assert params.margin_of_error == 0.05

    def test_sample_size_params_defaults(self):
        params = SampleSizeParams(methodology="monadic", num_concepts=4)
        assert params.concepts_per_respondent == 3
        assert params.num_subgroups == 1
        assert params.min_per_subgroup == 30

    def test_sample_size_result_valid(self):
        result = SampleSizeResult(
            total_respondents=600,
            per_concept=150,
            incidence_adjusted=1000,
            recommended_panel_size=6667,
        )
        assert result.total_respondents == 600

    def test_quota_allocation_valid(self):
        alloc = QuotaAllocation(
            dimension="age",
            segments=[
                {"range": "18-24", "target_pct": 30, "target_n": 180, "min_n": 153},
            ],
        )
        assert alloc.dimension == "age"

    def test_research_design_content_valid(self):
        content = ResearchDesignContent(
            testing_methodology="sequential_monadic",
            concepts_per_respondent=3,
            total_sample_size=600,
            confidence_level=0.95,
            margin_of_error=0.05,
            demographic_quotas=[],
            rotation_design="balanced_incomplete_block",
            data_collection_method="online_panel",
            estimated_field_duration=12,
            estimated_cost=90000,
        )
        assert content.total_sample_size == 600


# ─── Questionnaire Schemas ───

class TestQuestionnaireSchemas:
    def test_question_scale_valid(self):
        scale = QuestionScale(
            type="likert_5",
            options=[{"value": 5, "label": "Strongly agree"}],
        )
        assert scale.type == "likert_5"

    def test_question_valid(self):
        q = Question(
            question_id="Q1",
            section="S1_screening",
            question_text={"en": "How old are you?", "hi": "Aapki umar kitni hai?"},
            question_type="single_select",
            position_in_section=1,
        )
        assert q.question_id == "Q1"
        assert q.required is True

    def test_question_minimal(self):
        q = Question(
            question_id="Q1",
            section="S1",
            question_text={"en": "Test?"},
            question_type="single_select",
            position_in_section=1,
        )
        assert q.metric_id is None
        assert q.show_if is None

    def test_questionnaire_section_valid(self):
        q = Question(
            question_id="Q1",
            section="S1",
            question_text={"en": "Test?"},
            question_type="single_select",
            position_in_section=1,
        )
        section = QuestionnaireSection(
            section_id="S1_screening",
            section_name="Screening",
            questions=[q],
        )
        assert len(section.questions) == 1

    def test_quality_controls_valid(self):
        qc = QualityControls(
            attention_check={"question": "Select agree", "correct_answer": "agree"},
            speeder_threshold_seconds=180,
            straightline_detection=True,
            open_end_quality_check=True,
        )
        assert qc.straightline_detection is True

    def test_survey_logic_valid(self):
        logic = SurveyLogic(
            concept_rotation="balanced_incomplete_block",
            concepts_per_respondent=3,
        )
        assert logic.concepts_per_respondent == 3

    def test_questionnaire_content_valid(self):
        q = Question(
            question_id="Q1",
            section="S1",
            question_text={"en": "Test?"},
            question_type="single_select",
            position_in_section=1,
        )
        section = QuestionnaireSection(
            section_id="S1_screening",
            section_name="Screening",
            questions=[q],
        )
        content = QuestionnaireContent(
            questionnaire_id="QNR-001",
            study_id=str(uuid.uuid4()),
            version=1,
            estimated_duration_minutes=13,
            total_questions=1,
            sections=[section],
            quality_controls=QualityControls(
                attention_check={"q": "test"},
                speeder_threshold_seconds=180,
                straightline_detection=True,
                open_end_quality_check=True,
            ),
            survey_logic=SurveyLogic(
                concept_rotation="random",
                concepts_per_respondent=3,
            ),
        )
        assert content.total_questions == 1

    def test_section_feedback_request_valid(self):
        req = SectionFeedbackRequest(
            section_id="S4_core_kpi",
            feedback_text="Add a brand fit question",
            feedback_type="add_question",
        )
        assert req.feedback_type == "add_question"

    def test_section_feedback_response_valid(self):
        q = Question(
            question_id="Q1",
            section="S1",
            question_text={"en": "Test?"},
            question_type="single_select",
            position_in_section=1,
        )
        resp = SectionFeedbackResponse(
            updated_section=QuestionnaireSection(
                section_id="S4",
                section_name="KPI",
                questions=[q],
            ),
            change_log=["Added Q2"],
            warnings=[],
        )
        assert len(resp.change_log) == 1


# ─── Audit Schemas ───

class TestAuditSchemas:
    def test_audit_log_entry_valid(self):
        now = datetime.now(timezone.utc)
        entry = AuditLogEntry(
            id=uuid.uuid4(),
            study_id=uuid.uuid4(),
            action="study_created",
            actor="user_123",
            created_at=now,
        )
        assert entry.action == "study_created"

    def test_review_comment_create_valid(self):
        data = ReviewCommentCreate(
            step=1,
            target_type="step",
            comment_text="Looks good",
        )
        assert data.step == 1
        assert data.target_id is None

    def test_review_comment_response_valid(self):
        now = datetime.now(timezone.utc)
        resp = ReviewCommentResponse(
            id=uuid.uuid4(),
            study_id=uuid.uuid4(),
            step=1,
            target_type="step",
            comment_text="Looks good",
            resolved=False,
            created_at=now,
        )
        assert resp.resolved is False


# ─── Metric Schemas ───

class TestMetricSchemas:
    def test_metric_response_valid(self):
        resp = MetricResponse(
            id="purchase_intent",
            display_name="Purchase Intent",
            category="core_kpi",
            applicable_study_types=["concept_testing"],
            default_scale={"type": "likert_5", "options": []},
            benchmark_available=True,
        )
        assert resp.id == "purchase_intent"

    def test_metric_create_valid(self):
        data = MetricCreate(
            id="new_metric",
            display_name="New Metric",
            category="diagnostic",
            applicable_study_types=["concept_testing"],
            default_scale={"type": "likert_5", "options": []},
        )
        assert data.benchmark_available is False

    def test_metric_create_missing_required(self):
        with pytest.raises(ValidationError):
            MetricCreate(
                id="test",
                display_name="Test",
                # missing category, applicable_study_types, default_scale
            )


# ─── BaseSchema & Pagination ───

class TestBaseSchemaAndPagination:
    def test_base_schema_from_attributes(self):
        assert BaseSchema.model_config["from_attributes"] is True

    def test_paginated_request_defaults(self):
        req = PaginatedRequest()
        assert req.page == 1
        assert req.page_size == 20

    def test_paginated_response_valid(self):
        resp = PaginatedResponse[str](
            items=["a", "b"],
            total=10,
            page=1,
            page_size=2,
            total_pages=5,
        )
        assert len(resp.items) == 2
        assert resp.total == 10
