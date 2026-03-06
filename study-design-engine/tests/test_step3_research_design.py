"""Tests for Step 3 Research Design — 28+ tests.

Covers ResearchDesignService, router registration, prompt loading,
and schema validation for the research design workflow.
"""

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.research_design import (
    ResearchDesignContent,
    ResearchDesignResponse,
    SampleSizeParams,
    SampleSizeResult,
    QuotaAllocation,
)
from app.schemas.study import StepVersionResponse
from app.services.prompt_service import PromptService
from app.services.research_design_service import ResearchDesignService
from app.services.sample_calculator import SampleCalculator


# ─── Helpers ─────────────────────────────────────────────────────


def _make_study(status: str = "step_2_locked") -> MagicMock:
    study = MagicMock()
    study.id = uuid.uuid4()
    study.brand_id = uuid.uuid4()
    study.status = status
    study.question = "Which concept resonates best?"
    study.title = "Snack Concept Test"
    study.brand_name = "TestBrand"
    study.category = "snacks"
    study.context = {}
    study.study_metadata = {}
    study.created_at = datetime.now(timezone.utc)
    study.updated_at = datetime.now(timezone.utc)
    return study


def _mock_step1_content() -> dict:
    return {
        "study_type": "concept_testing",
        "study_type_confidence": 0.92,
        "recommended_title": "Snack Concept Test",
        "recommended_metrics": ["purchase_intent", "uniqueness"],
        "recommended_audience": {"age": "18-45", "geography": "urban"},
        "methodology_family": "sequential_monadic",
        "methodology_rationale": "Best for multi-concept testing",
    }


def _mock_concepts() -> list[dict]:
    return [
        {"concept_index": 1, "version": 1, "status": "approved", "components": {"name": "Concept A"}},
        {"concept_index": 2, "version": 1, "status": "approved", "components": {"name": "Concept B"}},
        {"concept_index": 3, "version": 1, "status": "approved", "components": {"name": "Concept C"}},
    ]


def _mock_llm_response() -> dict:
    return {
        "testing_methodology": "sequential_monadic",
        "concepts_per_respondent": 3,
        "confidence_level": 0.95,
        "margin_of_error": 0.05,
        "rotation_design": "balanced_incomplete_block",
        "data_collection_method": "online_panel",
        "survey_language": ["english"],
        "demographic_quotas": [
            {
                "dimension": "gender",
                "segments": [
                    {"range": "male", "target_pct": 50},
                    {"range": "female", "target_pct": 50},
                ],
            },
        ],
        "rationale": "Sequential monadic is cost-efficient for 3 concepts.",
    }


def _make_step_version(
    study_id: uuid.UUID,
    step: int = 3,
    version: int = 1,
    status: str = "draft",
    content: dict | None = None,
) -> MagicMock:
    sv = MagicMock()
    sv.id = uuid.uuid4()
    sv.study_id = study_id
    sv.step = step
    sv.version = version
    sv.status = status
    sv.content = content or {
        "testing_methodology": "sequential_monadic",
        "concepts_per_respondent": 3,
        "total_sample_size": 75,
        "confidence_level": 0.95,
        "margin_of_error": 0.05,
        "demographic_quotas": [],
        "rotation_design": "balanced_incomplete_block",
        "data_collection_method": "online_panel",
        "survey_language": ["english"],
        "estimated_field_duration": 3,
        "estimated_cost": 11250,
    }
    sv.ai_rationale = {"llm_recommendations": _mock_llm_response()}
    sv.locked_at = None
    sv.locked_by = None
    sv.created_at = datetime.now(timezone.utc)
    return sv


# ─── ResearchDesignService: generate_design ──────────────────────


class TestGenerateDesign:
    @pytest.mark.asyncio
    async def test_generate_design_success(self):
        study = _make_study("step_2_locked")
        step1_sv = MagicMock()
        step1_sv.content = _mock_step1_content()

        mock_db = AsyncMock()

        # First call: _get_study
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study

        # Second call: _load_step_content (step 1)
        step1_result = MagicMock()
        step1_result.scalar_one_or_none.return_value = step1_sv

        # Third call: _load_concepts
        concept_mocks = []
        for c in _mock_concepts():
            cm = MagicMock()
            cm.concept_index = c["concept_index"]
            cm.version = c["version"]
            cm.status = c["status"]
            cm.components = c["components"]
            concept_mocks.append(cm)
        concepts_result = MagicMock()
        concepts_result.scalars.return_value.all.return_value = concept_mocks

        # Fourth call: _next_version (no existing step 3)
        version_result = MagicMock()
        version_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(
            side_effect=[study_result, step1_result, concepts_result, version_result]
        )

        # Mock the committed step_version via refresh
        async def mock_refresh(obj):
            obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        mock_llm = AsyncMock()
        mock_llm.generate_json = AsyncMock(return_value=_mock_llm_response())

        mock_prompts = MagicMock()
        mock_prompts.format_prompt = MagicMock(return_value="formatted prompt")

        service = ResearchDesignService(llm_client=mock_llm, prompt_service=mock_prompts)
        result = await service.generate_design(study.id, mock_db)

        assert result.step == 3
        assert result.version == 1
        assert result.status == "review"
        assert "testing_methodology" in result.content

    @pytest.mark.asyncio
    async def test_generate_design_study_not_found_raises(self):
        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result_mock)

        service = ResearchDesignService(llm_client=AsyncMock(), prompt_service=MagicMock())
        with pytest.raises(ValueError, match="not found"):
            await service.generate_design(uuid.uuid4(), mock_db)

    @pytest.mark.asyncio
    async def test_generate_design_wrong_status_raises(self):
        study = _make_study("step_1_locked")  # not step_2_locked

        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = study
        mock_db.execute = AsyncMock(return_value=result_mock)

        service = ResearchDesignService(llm_client=AsyncMock(), prompt_service=MagicMock())
        with pytest.raises(ValueError, match="Cannot generate Step 3"):
            await service.generate_design(study.id, mock_db)

    @pytest.mark.asyncio
    async def test_generate_design_calls_llm(self):
        study = _make_study("step_2_locked")
        step1_sv = MagicMock()
        step1_sv.content = _mock_step1_content()

        mock_db = AsyncMock()

        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study

        step1_result = MagicMock()
        step1_result.scalar_one_or_none.return_value = step1_sv

        concept_mocks = []
        for c in _mock_concepts():
            cm = MagicMock()
            cm.concept_index = c["concept_index"]
            cm.version = c["version"]
            cm.status = c["status"]
            cm.components = c["components"]
            concept_mocks.append(cm)
        concepts_result = MagicMock()
        concepts_result.scalars.return_value.all.return_value = concept_mocks

        version_result = MagicMock()
        version_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(
            side_effect=[study_result, step1_result, concepts_result, version_result]
        )
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        async def mock_refresh(obj):
            obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        mock_llm = AsyncMock()
        mock_llm.generate_json = AsyncMock(return_value=_mock_llm_response())

        mock_prompts = MagicMock()
        mock_prompts.format_prompt = MagicMock(return_value="prompt text")

        service = ResearchDesignService(llm_client=mock_llm, prompt_service=mock_prompts)
        await service.generate_design(study.id, mock_db)

        mock_llm.generate_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_design_uses_sample_calculator(self):
        """Ensure SampleCalculator is used for the deterministic part."""
        study = _make_study("step_2_locked")
        step1_sv = MagicMock()
        step1_sv.content = _mock_step1_content()

        mock_db = AsyncMock()

        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study

        step1_result = MagicMock()
        step1_result.scalar_one_or_none.return_value = step1_sv

        concept_mocks = []
        for c in _mock_concepts():
            cm = MagicMock()
            cm.concept_index = c["concept_index"]
            cm.version = c["version"]
            cm.status = c["status"]
            cm.components = c["components"]
            concept_mocks.append(cm)
        concepts_result = MagicMock()
        concepts_result.scalars.return_value.all.return_value = concept_mocks

        version_result = MagicMock()
        version_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(
            side_effect=[study_result, step1_result, concepts_result, version_result]
        )
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        async def mock_refresh(obj):
            obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        mock_llm = AsyncMock()
        mock_llm.generate_json = AsyncMock(return_value=_mock_llm_response())

        mock_prompts = MagicMock()
        mock_prompts.format_prompt = MagicMock(return_value="prompt text")

        service = ResearchDesignService(llm_client=mock_llm, prompt_service=mock_prompts)

        with patch.object(SampleCalculator, "calculate_sample_size", wraps=SampleCalculator.calculate_sample_size) as spy:
            result = await service.generate_design(study.id, mock_db)
            spy.assert_called_once()


# ─── ResearchDesignService: edit_design ──────────────────────────


class TestEditDesign:
    @pytest.mark.asyncio
    async def test_edit_design_success(self):
        study = _make_study("step_3_draft")
        study_id = study.id

        existing_sv = _make_step_version(study_id, step=3, version=1)

        mock_db = AsyncMock()

        # _get_study
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study

        # _load_latest_step_version
        sv_result = MagicMock()
        sv_result.scalar_one_or_none.return_value = existing_sv

        # _load_concepts
        concepts_result = MagicMock()
        concepts_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[study_result, sv_result, concepts_result]
        )
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        async def mock_refresh(obj):
            obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        service = ResearchDesignService(llm_client=AsyncMock(), prompt_service=MagicMock())
        result = await service.edit_design(
            study_id, {"data_collection_method": "capi"}, mock_db
        )

        assert result.step == 3
        assert result.version == 2

    @pytest.mark.asyncio
    async def test_edit_design_locked_raises(self):
        study = _make_study("step_3_locked")

        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = study
        mock_db.execute = AsyncMock(return_value=result_mock)

        service = ResearchDesignService(llm_client=AsyncMock(), prompt_service=MagicMock())
        with pytest.raises(ValueError, match="Cannot edit Step 3"):
            await service.edit_design(study.id, {"margin_of_error": 0.03}, mock_db)

    @pytest.mark.asyncio
    async def test_edit_design_wrong_step_raises(self):
        study = _make_study("step_1_draft")

        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = study
        mock_db.execute = AsyncMock(return_value=result_mock)

        service = ResearchDesignService(llm_client=AsyncMock(), prompt_service=MagicMock())
        with pytest.raises(ValueError, match="Cannot edit Step 3"):
            await service.edit_design(study.id, {"margin_of_error": 0.03}, mock_db)

    @pytest.mark.asyncio
    async def test_edit_design_no_existing_version_raises(self):
        study = _make_study("step_3_draft")

        mock_db = AsyncMock()

        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study

        sv_result = MagicMock()
        sv_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[study_result, sv_result])

        service = ResearchDesignService(llm_client=AsyncMock(), prompt_service=MagicMock())
        with pytest.raises(ValueError, match="No existing Step 3"):
            await service.edit_design(study.id, {"margin_of_error": 0.03}, mock_db)


# ─── ResearchDesignService: lock_design ──────────────────────────


class TestLockDesign:
    @pytest.mark.asyncio
    async def test_lock_design_success(self):
        study = _make_study("step_3_review")
        study_id = study.id
        user_id = str(uuid.uuid4())

        existing_sv = _make_step_version(study_id, step=3, version=1, status="draft")

        mock_db = AsyncMock()

        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study

        sv_result = MagicMock()
        sv_result.scalar_one_or_none.return_value = existing_sv

        mock_db.execute = AsyncMock(side_effect=[study_result, sv_result])
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        service = ResearchDesignService(llm_client=AsyncMock(), prompt_service=MagicMock())
        result = await service.lock_design(study_id, user_id, mock_db)

        assert result.status == "locked"
        assert study.status == "step_3_locked"

    @pytest.mark.asyncio
    async def test_lock_design_wrong_status_raises(self):
        study = _make_study("step_3_draft")

        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = study
        mock_db.execute = AsyncMock(return_value=result_mock)

        service = ResearchDesignService(llm_client=AsyncMock(), prompt_service=MagicMock())
        with pytest.raises(ValueError, match="Cannot lock Step 3"):
            await service.lock_design(study.id, str(uuid.uuid4()), mock_db)

    @pytest.mark.asyncio
    async def test_lock_design_no_version_raises(self):
        study = _make_study("step_3_review")

        mock_db = AsyncMock()

        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study

        sv_result = MagicMock()
        sv_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[study_result, sv_result])

        service = ResearchDesignService(llm_client=AsyncMock(), prompt_service=MagicMock())
        with pytest.raises(ValueError, match="No Step 3 design exists"):
            await service.lock_design(study.id, str(uuid.uuid4()), mock_db)


# ─── Schema Validation ──────────────────────────────────────────


class TestResearchDesignSchemaIntegration:
    def test_research_design_content_all_fields(self):
        content = ResearchDesignContent(
            testing_methodology="sequential_monadic",
            concepts_per_respondent=3,
            total_sample_size=250,
            confidence_level=0.95,
            margin_of_error=0.05,
            demographic_quotas=[],
            rotation_design="balanced_incomplete_block",
            data_collection_method="online_panel",
            survey_language=["english", "hindi"],
            estimated_field_duration=5,
            estimated_cost=37500,
        )
        assert content.total_sample_size == 250
        assert content.survey_language == ["english", "hindi"]

    def test_research_design_content_default_language(self):
        content = ResearchDesignContent(
            testing_methodology="monadic",
            concepts_per_respondent=1,
            total_sample_size=600,
            confidence_level=0.95,
            margin_of_error=0.05,
            demographic_quotas=[],
            rotation_design="full_rotation",
            data_collection_method="online_panel",
            estimated_field_duration=12,
            estimated_cost=90000,
        )
        assert content.survey_language == ["english"]

    def test_sample_size_params_validation(self):
        params = SampleSizeParams(
            methodology="monadic",
            num_concepts=4,
            confidence_level=0.95,
            margin_of_error=0.05,
        )
        assert params.methodology == "monadic"
        assert params.concepts_per_respondent == 3

    def test_step_version_response_with_content(self):
        now = datetime.now(timezone.utc)
        resp = StepVersionResponse(
            id=uuid.uuid4(),
            study_id=uuid.uuid4(),
            step=3,
            version=1,
            status="draft",
            content={
                "testing_methodology": "sequential_monadic",
                "total_sample_size": 250,
            },
            ai_rationale={"llm_recommendations": {}},
            created_at=now,
        )
        assert resp.step == 3
        assert resp.content["total_sample_size"] == 250

    def test_research_design_response_schema(self):
        now = datetime.now(timezone.utc)
        resp = ResearchDesignResponse(
            id=uuid.uuid4(),
            study_id=uuid.uuid4(),
            step=3,
            version=1,
            content={"testing_methodology": "monadic"},
            ai_rationale={"note": "test"},
            created_at=now,
        )
        assert resp.step == 3
        assert resp.ai_rationale["note"] == "test"


# ─── Prompt Loading ──────────────────────────────────────────────


class TestPromptTemplateLoading:
    def test_research_design_prompt_file_exists(self):
        """The prompt template file must exist in the prompts directory."""
        prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "prompts",
        )
        filepath = os.path.join(prompts_dir, "research_design_generator.txt")
        assert os.path.exists(filepath), f"Prompt file not found: {filepath}"

    def test_prompt_template_has_placeholders(self):
        prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "prompts",
        )
        filepath = os.path.join(prompts_dir, "research_design_generator.txt")
        with open(filepath) as f:
            content = f.read()
        assert "{study_brief_json}" in content
        assert "{concepts_json}" in content
        assert "{selected_metrics_json}" in content

    def test_prompt_service_can_load_template(self):
        prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "prompts",
        )
        svc = PromptService(prompts_dir=prompts_dir)
        template = svc.load_template("research_design_generator")
        assert len(template) > 100

    def test_prompt_service_can_format_template(self):
        prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "prompts",
        )
        svc = PromptService(prompts_dir=prompts_dir)
        result = svc.format_prompt(
            "research_design_generator",
            study_brief_json='{"study_type": "concept_testing"}',
            concepts_json='[{"name": "A"}]',
            selected_metrics_json='["purchase_intent"]',
        )
        assert "concept_testing" in result
        assert "purchase_intent" in result


# ─── Router Registration ─────────────────────────────────────────


class TestRouterRegistration:
    def test_router_prefix(self):
        from app.routers.research_design import router

        assert router.prefix == "/api/v1/studies/{study_id}"

    def test_router_tags(self):
        from app.routers.research_design import router

        assert "Research Design" in router.tags

    def test_router_has_generate_route(self):
        from app.routers.research_design import router

        paths = [r.path for r in router.routes]
        matching = [p for p in paths if p.endswith("/steps/3/generate")]
        assert len(matching) == 1

    def test_router_has_edit_route(self):
        from app.routers.research_design import router

        paths = [r.path for r in router.routes]
        matching = [p for p in paths if p.endswith("/steps/3")]
        assert len(matching) == 1

    def test_router_has_lock_route(self):
        from app.routers.research_design import router

        paths = [r.path for r in router.routes]
        matching = [p for p in paths if p.endswith("/steps/3/lock")]
        assert len(matching) == 1

    def test_router_generate_is_post(self):
        from app.routers.research_design import router

        for route in router.routes:
            if getattr(route, "path", None) == "/steps/3/generate":
                assert "POST" in route.methods

    def test_router_edit_is_patch(self):
        from app.routers.research_design import router

        for route in router.routes:
            if getattr(route, "path", None) == "/steps/3":
                assert "PATCH" in route.methods

    def test_router_lock_is_post(self):
        from app.routers.research_design import router

        for route in router.routes:
            if getattr(route, "path", None) == "/steps/3/lock":
                assert "POST" in route.methods


# ─── Service Instantiation ───────────────────────────────────────


class TestServiceInstantiation:
    def test_service_creates_with_defaults(self):
        service = ResearchDesignService()
        assert service.llm is not None
        assert service.prompts is not None

    def test_service_accepts_custom_llm(self):
        mock_llm = AsyncMock()
        service = ResearchDesignService(llm_client=mock_llm)
        assert service.llm is mock_llm

    def test_service_accepts_custom_prompt_service(self):
        mock_prompts = MagicMock()
        service = ResearchDesignService(prompt_service=mock_prompts)
        assert service.prompts is mock_prompts
