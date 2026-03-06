"""Tests for Step 2 — Concept Board Builder — 45+ tests.

Covers:
 - Concept schemas (validation, defaults, edge cases)
 - ConceptBoardService methods with mocked DB and LLM
 - Prompt template loading for concept_refiner and comparability_auditor
 - Router registration and endpoint existence
"""

import copy
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.common import ConceptStatus
from app.schemas.concept import (
    ComparabilityCheckResponse,
    ConceptComponent,
    ConceptComponents,
    ConceptCreate,
    ConceptRefineResponse,
    ConceptResponse,
)
from app.services.concept_board_service import (
    ConceptBoardService,
    DEFAULT_NUM_CONCEPTS,
    DEFAULT_TEMPLATE_COMPONENTS,
)
from app.services.prompt_service import PromptService
from app.services.state_machine import StudyStateMachine


# ═══════════════════════════════════════════════════════════════════════════
# Helpers / Fixtures
# ═══════════════════════════════════════════════════════════════════════════

def _make_study(status: str = "step_1_locked", **overrides):
    study = MagicMock()
    study.id = overrides.get("id", uuid.uuid4())
    study.brand_id = overrides.get("brand_id", uuid.uuid4())
    study.status = status
    study.question = overrides.get("question", "Which concept works best?")
    study.title = overrides.get("title", "Test Study")
    study.brand_name = overrides.get("brand_name", "TestBrand")
    study.category = overrides.get("category", "snacks")
    study.context = overrides.get("context", {"competitor_brands": ["BrandA", "BrandB"]})
    study.study_metadata = overrides.get("study_metadata", {})
    study.created_at = datetime.now(timezone.utc)
    study.updated_at = datetime.now(timezone.utc)
    return study


def _make_concept(study_id=None, concept_index=1, status="raw", **overrides):
    concept = MagicMock()
    concept.id = overrides.get("id", uuid.uuid4())
    concept.study_id = study_id or uuid.uuid4()
    concept.concept_index = concept_index
    concept.version = overrides.get("version", 1)
    concept.status = status
    concept.components = overrides.get("components", copy.deepcopy(DEFAULT_TEMPLATE_COMPONENTS))
    concept.comparability_flags = overrides.get("comparability_flags", [])
    concept.image_url = overrides.get("image_url", None)
    concept.image_version = overrides.get("image_version", 0)
    concept.created_at = datetime.now(timezone.utc)
    concept.updated_at = datetime.now(timezone.utc)
    return concept


def _make_step_version(study_id=None, step=1, version=1, status="locked"):
    sv = MagicMock()
    sv.id = uuid.uuid4()
    sv.study_id = study_id or uuid.uuid4()
    sv.step = step
    sv.version = version
    sv.status = status
    sv.content = {
        "study_type": "concept_testing",
        "recommended_title": "Test Study",
        "recommended_metrics": ["purchase_intent"],
        "recommended_audience": {"age": "18-45"},
        "methodology_family": "sequential_monadic",
        "methodology_rationale": "Best for multi-concept testing",
    }
    sv.locked_at = datetime.now(timezone.utc)
    sv.locked_by = uuid.uuid4()
    sv.created_at = datetime.now(timezone.utc)
    return sv


def _mock_db_execute_factory(returns_by_call: list):
    """Create a db.execute mock that returns different results for sequential calls."""
    call_count = 0

    async def _execute(query):
        nonlocal call_count
        result = MagicMock()
        if call_count < len(returns_by_call):
            value = returns_by_call[call_count]
        else:
            value = None
        call_count += 1
        result.scalar_one_or_none = MagicMock(return_value=value)
        result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=value if isinstance(value, list) else [value] if value else [])))
        return result

    return _execute


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value="{}")
    llm.generate_json = AsyncMock(return_value={
        "refined_components": {
            "consumer_insight": {"refined": "Refined insight", "refinement_rationale": "Better framing"},
            "product_name": {"refined": "NewName", "refinement_rationale": "More memorable"},
            "key_benefit": {"refined": "Clear benefit", "refinement_rationale": "Single-minded"},
            "reasons_to_believe": {"refined": "Strong RTBs", "refinement_rationale": "Credibility chain"},
            "visual": {"refined_description": "Clean design", "refinement_rationale": "Neutral"},
            "price_format": {"refined_price": "$4.99", "refinement_rationale": "Category norm"},
        },
        "flags": ["Minor length imbalance"],
        "testability_score": 0.85,
    })
    return llm


@pytest.fixture
def mock_prompts():
    prompts = MagicMock(spec=PromptService)
    prompts.format_prompt = MagicMock(return_value="formatted prompt text")
    prompts.load_template = MagicMock(return_value="template {category}")
    return prompts


@pytest.fixture
def service(mock_llm, mock_prompts):
    return ConceptBoardService(llm_client=mock_llm, prompt_service=mock_prompts)


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.delete = AsyncMock()
    return db


# ═══════════════════════════════════════════════════════════════════════════
# 1. Schema Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestConceptSchemaValidation:
    """Tests for concept-related Pydantic schemas."""

    def test_concept_component_defaults(self):
        comp = ConceptComponent(raw_input="test")
        assert comp.refined is None
        assert comp.refinement_rationale is None
        assert comp.approved is False
        assert comp.brand_edit is None

    def test_concept_component_with_refinement(self):
        comp = ConceptComponent(
            raw_input="original",
            refined="improved",
            refinement_rationale="clarity",
            approved=True,
        )
        assert comp.refined == "improved"
        assert comp.approved is True

    def test_concept_component_brand_edit(self):
        comp = ConceptComponent(
            raw_input="original",
            brand_edit="client version",
        )
        assert comp.brand_edit == "client version"

    def test_concept_components_full(self):
        base = ConceptComponent(raw_input="test")
        cc = ConceptComponents(
            consumer_insight=base,
            product_name=base,
            key_benefit=base,
            reasons_to_believe=base,
            visual={"description": "A clean product shot"},
            price_format={"price": "$4.99", "format": "per unit"},
        )
        assert cc.consumer_insight.raw_input == "test"
        assert cc.visual["description"] == "A clean product shot"

    def test_concept_response_all_fields(self):
        now = datetime.now(timezone.utc)
        resp = ConceptResponse(
            id=uuid.uuid4(),
            study_id=uuid.uuid4(),
            concept_index=2,
            version=3,
            status="refined",
            components={"key_benefit": {"refined": "better"}},
            comparability_flags=["flag1"],
            image_url="https://example.com/img.png",
            created_at=now,
        )
        assert resp.version == 3
        assert resp.status == "refined"
        assert resp.image_url == "https://example.com/img.png"

    def test_concept_response_optional_fields_default(self):
        now = datetime.now(timezone.utc)
        resp = ConceptResponse(
            id=uuid.uuid4(),
            study_id=uuid.uuid4(),
            concept_index=1,
            version=1,
            status="raw",
            components={},
            created_at=now,
        )
        assert resp.comparability_flags is None
        assert resp.image_url is None

    def test_concept_refine_response_valid(self):
        resp = ConceptRefineResponse(
            concept_id=uuid.uuid4(),
            refined_components={"consumer_insight": {"refined": "text"}},
            flags=["flag1", "flag2"],
            testability_score=0.92,
        )
        assert resp.testability_score == 0.92
        assert len(resp.flags) == 2

    def test_concept_refine_response_empty_flags(self):
        resp = ConceptRefineResponse(
            concept_id=uuid.uuid4(),
            refined_components={},
            testability_score=0.5,
        )
        assert resp.flags == []

    def test_comparability_check_response_pass(self):
        resp = ComparabilityCheckResponse(
            overall_comparability="pass",
            issues=[],
            recommendation="All good",
        )
        assert resp.overall_comparability == "pass"

    def test_comparability_check_response_fail(self):
        resp = ComparabilityCheckResponse(
            overall_comparability="fail",
            issues=["Length imbalance", "Loaded language in concept 2"],
            recommendation="Revise concepts 2 and 3",
        )
        assert len(resp.issues) == 2

    def test_comparability_check_response_warning(self):
        resp = ComparabilityCheckResponse(
            overall_comparability="warning",
            issues=["Minor price spread"],
            recommendation="Consider narrowing price range",
        )
        assert resp.overall_comparability == "warning"

    def test_concept_status_enum_values(self):
        assert ConceptStatus.raw == "raw"
        assert ConceptStatus.refined == "refined"
        assert ConceptStatus.approved == "approved"

    def test_concept_create_schema(self):
        base = ConceptComponent(raw_input="test")
        cc = ConceptComponents(
            consumer_insight=base,
            product_name=base,
            key_benefit=base,
            reasons_to_believe=base,
            visual={"description": "image"},
            price_format={"price": "5.99", "format": "per pack"},
        )
        create = ConceptCreate(components=cc)
        assert create.components.consumer_insight.raw_input == "test"


# ═══════════════════════════════════════════════════════════════════════════
# 2. Service Tests — generate_templates
# ═══════════════════════════════════════════════════════════════════════════

class TestGenerateTemplates:
    """Tests for ConceptBoardService.generate_templates."""

    @pytest.mark.asyncio
    async def test_generate_templates_creates_concepts(self, service, mock_db):
        study = _make_study("step_1_locked")
        sv = _make_step_version(study_id=study.id)

        call_count = 0
        async def _exec(query):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=study)
            elif call_count == 1:
                result.scalar_one_or_none = MagicMock(return_value=sv)
            else:
                result.scalar_one_or_none = MagicMock(return_value=None)
            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=_exec)

        async def _refresh(obj):
            if not hasattr(obj, 'created_at') or obj.created_at is None:
                obj.created_at = datetime.now(timezone.utc)
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = uuid.uuid4()

        mock_db.refresh = AsyncMock(side_effect=_refresh)

        results = await service.generate_templates(study.id, mock_db)
        assert len(results) == DEFAULT_NUM_CONCEPTS
        assert mock_db.add.call_count == DEFAULT_NUM_CONCEPTS

    @pytest.mark.asyncio
    async def test_generate_templates_custom_count(self, service, mock_db):
        study = _make_study("step_1_locked")
        sv = _make_step_version(study_id=study.id)

        call_count = 0
        async def _exec(query):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=study)
            elif call_count == 1:
                result.scalar_one_or_none = MagicMock(return_value=sv)
            else:
                result.scalar_one_or_none = MagicMock(return_value=None)
            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=_exec)

        async def _refresh(obj):
            if not hasattr(obj, 'created_at') or obj.created_at is None:
                obj.created_at = datetime.now(timezone.utc)
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = uuid.uuid4()

        mock_db.refresh = AsyncMock(side_effect=_refresh)

        results = await service.generate_templates(study.id, mock_db, num_concepts=5)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_generate_templates_rejects_non_locked_step1(self, service, mock_db):
        study = _make_study("step_1_draft")
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=study)
        ))
        with pytest.raises(ValueError, match="Cannot generate concepts"):
            await service.generate_templates(study.id, mock_db)

    @pytest.mark.asyncio
    async def test_generate_templates_rejects_init_status(self, service, mock_db):
        study = _make_study("init")
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=study)
        ))
        with pytest.raises(ValueError, match="Cannot generate concepts"):
            await service.generate_templates(study.id, mock_db)

    @pytest.mark.asyncio
    async def test_generate_templates_transitions_to_step_2_draft(self, service, mock_db):
        study = _make_study("step_1_locked")
        sv = _make_step_version(study_id=study.id)

        call_count = 0
        async def _exec(query):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=study)
            elif call_count == 1:
                result.scalar_one_or_none = MagicMock(return_value=sv)
            else:
                result.scalar_one_or_none = MagicMock(return_value=None)
            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=_exec)

        async def _refresh(obj):
            if not hasattr(obj, 'created_at') or obj.created_at is None:
                obj.created_at = datetime.now(timezone.utc)
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = uuid.uuid4()

        mock_db.refresh = AsyncMock(side_effect=_refresh)

        await service.generate_templates(study.id, mock_db)
        assert study.status == "step_2_draft"

    @pytest.mark.asyncio
    async def test_generate_templates_study_not_found(self, service, mock_db):
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        with pytest.raises(ValueError, match="not found"):
            await service.generate_templates(uuid.uuid4(), mock_db)


# ═══════════════════════════════════════════════════════════════════════════
# 3. Service Tests — update_concept
# ═══════════════════════════════════════════════════════════════════════════

class TestUpdateConcept:
    """Tests for ConceptBoardService.update_concept."""

    @pytest.mark.asyncio
    async def test_update_concept_success(self, service, mock_db):
        study = _make_study("step_2_draft")
        concept = _make_concept(study_id=study.id)

        call_count = 0
        async def _exec(query):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=study)
            else:
                result.scalar_one_or_none = MagicMock(return_value=concept)
            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=_exec)
        mock_db.refresh = AsyncMock()

        new_components = {"consumer_insight": {"raw_input": "Updated insight"}}
        result = await service.update_concept(study.id, concept.id, new_components, mock_db)
        assert concept.components == new_components
        assert concept.version == 2  # incremented

    @pytest.mark.asyncio
    async def test_update_concept_rejects_locked_step(self, service, mock_db):
        study = _make_study("step_2_locked")
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=study)
        ))
        with pytest.raises(ValueError, match="step 2 is locked"):
            await service.update_concept(study.id, uuid.uuid4(), {}, mock_db)

    @pytest.mark.asyncio
    async def test_update_concept_not_found(self, service, mock_db):
        study = _make_study("step_2_draft")

        call_count = 0
        async def _exec(query):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=study)
            else:
                result.scalar_one_or_none = MagicMock(return_value=None)
            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=_exec)
        with pytest.raises(ValueError, match="not found"):
            await service.update_concept(study.id, uuid.uuid4(), {}, mock_db)

    @pytest.mark.asyncio
    async def test_update_concept_increments_version(self, service, mock_db):
        study = _make_study("step_2_draft")
        concept = _make_concept(study_id=study.id, version=3)

        call_count = 0
        async def _exec(query):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=study)
            else:
                result.scalar_one_or_none = MagicMock(return_value=concept)
            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=_exec)
        mock_db.refresh = AsyncMock()

        await service.update_concept(study.id, concept.id, {"a": "b"}, mock_db)
        assert concept.version == 4


# ═══════════════════════════════════════════════════════════════════════════
# 4. Service Tests — refine_concept
# ═══════════════════════════════════════════════════════════════════════════

class TestRefineConcept:
    """Tests for ConceptBoardService.refine_concept."""

    @pytest.mark.asyncio
    async def test_refine_concept_success(self, service, mock_db, mock_llm):
        study = _make_study("step_2_draft")
        concept = _make_concept(study_id=study.id, status="raw")
        sv = _make_step_version(study_id=study.id)

        call_count = 0
        async def _exec(query):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=study)
            elif call_count == 1:
                result.scalar_one_or_none = MagicMock(return_value=concept)
            elif call_count == 2:
                result.scalar_one_or_none = MagicMock(return_value=sv)
            else:
                result.scalar_one_or_none = MagicMock(return_value=None)
            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=_exec)
        mock_db.refresh = AsyncMock()

        resp = await service.refine_concept(study.id, concept.id, mock_db)
        assert isinstance(resp, ConceptRefineResponse)
        assert concept.status == "refined"
        assert resp.testability_score == 0.85
        mock_llm.generate_json.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_refine_concept_rejects_non_raw(self, service, mock_db):
        study = _make_study("step_2_draft")
        concept = _make_concept(study_id=study.id, status="refined")

        call_count = 0
        async def _exec(query):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=study)
            else:
                result.scalar_one_or_none = MagicMock(return_value=concept)
            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=_exec)
        with pytest.raises(ValueError, match="must be in 'raw' status"):
            await service.refine_concept(study.id, concept.id, mock_db)

    @pytest.mark.asyncio
    async def test_refine_concept_rejects_approved(self, service, mock_db):
        study = _make_study("step_2_draft")
        concept = _make_concept(study_id=study.id, status="approved")

        call_count = 0
        async def _exec(query):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=study)
            else:
                result.scalar_one_or_none = MagicMock(return_value=concept)
            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=_exec)
        with pytest.raises(ValueError, match="must be in 'raw' status"):
            await service.refine_concept(study.id, concept.id, mock_db)

    @pytest.mark.asyncio
    async def test_refine_concept_calls_prompt_service(self, service, mock_db, mock_prompts):
        study = _make_study("step_2_draft")
        concept = _make_concept(study_id=study.id, status="raw")
        sv = _make_step_version(study_id=study.id)

        call_count = 0
        async def _exec(query):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=study)
            elif call_count == 1:
                result.scalar_one_or_none = MagicMock(return_value=concept)
            elif call_count == 2:
                result.scalar_one_or_none = MagicMock(return_value=sv)
            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=_exec)
        mock_db.refresh = AsyncMock()

        await service.refine_concept(study.id, concept.id, mock_db)
        mock_prompts.format_prompt.assert_called_once()
        call_kwargs = mock_prompts.format_prompt.call_args
        assert call_kwargs[0][0] == "concept_refiner"

    @pytest.mark.asyncio
    async def test_refine_concept_returns_flags(self, service, mock_db, mock_llm):
        study = _make_study("step_2_draft")
        concept = _make_concept(study_id=study.id, status="raw")
        sv = _make_step_version(study_id=study.id)

        call_count = 0
        async def _exec(query):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=study)
            elif call_count == 1:
                result.scalar_one_or_none = MagicMock(return_value=concept)
            elif call_count == 2:
                result.scalar_one_or_none = MagicMock(return_value=sv)
            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=_exec)
        mock_db.refresh = AsyncMock()

        resp = await service.refine_concept(study.id, concept.id, mock_db)
        assert "Minor length imbalance" in resp.flags


# ═══════════════════════════════════════════════════════════════════════════
# 5. Service Tests — approve_concept
# ═══════════════════════════════════════════════════════════════════════════

class TestApproveConcept:
    """Tests for ConceptBoardService.approve_concept."""

    @pytest.mark.asyncio
    async def test_approve_concept_sets_status(self, service, mock_db):
        study = _make_study("step_2_draft")
        concept = _make_concept(study_id=study.id, status="refined")

        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=concept)
        ))
        mock_db.refresh = AsyncMock()

        resp = await service.approve_concept(
            study.id, concept.id, {"consumer_insight": "refined"}, mock_db
        )
        assert concept.status == "approved"

    @pytest.mark.asyncio
    async def test_approve_concept_refined_choice(self, service, mock_db):
        study = _make_study("step_2_draft")
        components = copy.deepcopy(DEFAULT_TEMPLATE_COMPONENTS)
        concept = _make_concept(study_id=study.id, status="refined", components=components)

        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=concept)
        ))
        mock_db.refresh = AsyncMock()

        await service.approve_concept(
            study.id, concept.id,
            {"consumer_insight": "refined", "product_name": "brand_edit"},
            mock_db,
        )
        assert concept.components["consumer_insight"]["approved"] is True
        assert concept.components["product_name"]["approved"] is True

    @pytest.mark.asyncio
    async def test_approve_concept_with_dict_override(self, service, mock_db):
        study = _make_study("step_2_draft")
        components = copy.deepcopy(DEFAULT_TEMPLATE_COMPONENTS)
        concept = _make_concept(study_id=study.id, status="refined", components=components)

        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=concept)
        ))
        mock_db.refresh = AsyncMock()

        await service.approve_concept(
            study.id, concept.id,
            {"consumer_insight": {"raw_input": "Custom override", "approved": True}},
            mock_db,
        )
        assert concept.components["consumer_insight"]["raw_input"] == "Custom override"
        assert concept.components["consumer_insight"]["approved"] is True

    @pytest.mark.asyncio
    async def test_approve_concept_not_found(self, service, mock_db):
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        with pytest.raises(ValueError, match="not found"):
            await service.approve_concept(uuid.uuid4(), uuid.uuid4(), {}, mock_db)


# ═══════════════════════════════════════════════════════════════════════════
# 6. Service Tests — comparability_check
# ═══════════════════════════════════════════════════════════════════════════

class TestComparabilityCheck:
    """Tests for ConceptBoardService.comparability_check."""

    @pytest.mark.asyncio
    async def test_comparability_check_success(self, service, mock_db, mock_llm):
        study_id = uuid.uuid4()
        concepts = [
            _make_concept(study_id=study_id, concept_index=i, status="refined")
            for i in range(1, 4)
        ]

        mock_llm.generate_json = AsyncMock(return_value={
            "overall_comparability": "pass",
            "issues": [],
            "recommendation": "All concepts are comparable",
        })

        result_mock = MagicMock()
        result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=concepts)))
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.commit = AsyncMock()

        resp = await service.comparability_check(study_id, mock_db)
        assert isinstance(resp, ComparabilityCheckResponse)
        assert resp.overall_comparability == "pass"

    @pytest.mark.asyncio
    async def test_comparability_check_with_issues(self, service, mock_db, mock_llm):
        study_id = uuid.uuid4()
        concepts = [
            _make_concept(study_id=study_id, concept_index=i)
            for i in range(1, 4)
        ]

        mock_llm.generate_json = AsyncMock(return_value={
            "overall_comparability": "fail",
            "issues": ["Length imbalance between concepts 1 and 3", "Loaded language in concept 2"],
            "recommendation": "Revise concept 2 language and balance lengths",
        })

        result_mock = MagicMock()
        result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=concepts)))
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.commit = AsyncMock()

        resp = await service.comparability_check(study_id, mock_db)
        assert resp.overall_comparability == "fail"
        assert len(resp.issues) == 2

    @pytest.mark.asyncio
    async def test_comparability_check_no_concepts(self, service, mock_db):
        result_mock = MagicMock()
        result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        mock_db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(ValueError, match="No concepts found"):
            await service.comparability_check(uuid.uuid4(), mock_db)

    @pytest.mark.asyncio
    async def test_comparability_check_calls_prompt(self, service, mock_db, mock_llm, mock_prompts):
        study_id = uuid.uuid4()
        concepts = [_make_concept(study_id=study_id, concept_index=1)]

        mock_llm.generate_json = AsyncMock(return_value={
            "overall_comparability": "pass",
            "issues": [],
            "recommendation": "OK",
        })

        result_mock = MagicMock()
        result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=concepts)))
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.commit = AsyncMock()

        await service.comparability_check(study_id, mock_db)
        mock_prompts.format_prompt.assert_called_once()
        assert mock_prompts.format_prompt.call_args[0][0] == "comparability_auditor"

    @pytest.mark.asyncio
    async def test_comparability_stores_flags_on_concepts(self, service, mock_db, mock_llm):
        study_id = uuid.uuid4()
        concepts = [
            _make_concept(study_id=study_id, concept_index=i)
            for i in range(1, 3)
        ]
        issues = ["Issue A", "Issue B"]

        mock_llm.generate_json = AsyncMock(return_value={
            "overall_comparability": "warning",
            "issues": issues,
            "recommendation": "Fix issues",
        })

        result_mock = MagicMock()
        result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=concepts)))
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.commit = AsyncMock()

        await service.comparability_check(study_id, mock_db)
        for c in concepts:
            assert c.comparability_flags == issues


# ═══════════════════════════════════════════════════════════════════════════
# 7. Service Tests — render_image
# ═══════════════════════════════════════════════════════════════════════════

class TestRenderImage:
    """Tests for ConceptBoardService.render_image."""

    @pytest.mark.asyncio
    async def test_render_image_generates_url(self, service, mock_db):
        study_id = uuid.uuid4()
        concept = _make_concept(study_id=study_id, image_version=0)

        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=concept)
        ))
        mock_db.refresh = AsyncMock()

        resp = await service.render_image(study_id, concept.id, mock_db)
        assert concept.image_version == 1
        assert "render_v1.png" in concept.image_url
        assert str(study_id) in concept.image_url

    @pytest.mark.asyncio
    async def test_render_image_increments_version(self, service, mock_db):
        study_id = uuid.uuid4()
        concept = _make_concept(study_id=study_id, image_version=2)

        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=concept)
        ))
        mock_db.refresh = AsyncMock()

        await service.render_image(study_id, concept.id, mock_db)
        assert concept.image_version == 3
        assert "render_v3.png" in concept.image_url

    @pytest.mark.asyncio
    async def test_render_image_concept_not_found(self, service, mock_db):
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        with pytest.raises(ValueError, match="not found"):
            await service.render_image(uuid.uuid4(), uuid.uuid4(), mock_db)


# ═══════════════════════════════════════════════════════════════════════════
# 8. Service Tests — lock_concepts
# ═══════════════════════════════════════════════════════════════════════════

class TestLockConcepts:
    """Tests for ConceptBoardService.lock_concepts."""

    @pytest.mark.asyncio
    async def test_lock_concepts_success(self, service, mock_db):
        study = _make_study("step_2_draft")
        user_id = str(uuid.uuid4())
        concepts = [
            _make_concept(study_id=study.id, concept_index=i, status="approved")
            for i in range(1, 4)
        ]

        call_count = 0
        async def _exec(query):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                # _get_study
                result.scalar_one_or_none = MagicMock(return_value=study)
            elif call_count == 1:
                # load all concepts
                result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=concepts)))
            elif call_count == 2:
                # existing step versions
                result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=_exec)
        mock_db.refresh = AsyncMock(side_effect=lambda sv: (
            setattr(sv, 'locked_at', datetime.now(timezone.utc)),
            setattr(sv, 'version', 1),
        ))

        resp = await service.lock_concepts(study.id, user_id, mock_db)
        assert resp["status"] == "locked"
        assert resp["step"] == 2
        assert study.status == "step_2_locked"

    @pytest.mark.asyncio
    async def test_lock_concepts_rejects_unapproved(self, service, mock_db):
        study = _make_study("step_2_draft")
        concepts = [
            _make_concept(study_id=study.id, concept_index=1, status="approved"),
            _make_concept(study_id=study.id, concept_index=2, status="raw"),
            _make_concept(study_id=study.id, concept_index=3, status="approved"),
        ]

        call_count = 0
        async def _exec(query):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=study)
            elif call_count == 1:
                result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=concepts)))
            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=_exec)
        with pytest.raises(ValueError, match="not approved"):
            await service.lock_concepts(study.id, str(uuid.uuid4()), mock_db)

    @pytest.mark.asyncio
    async def test_lock_concepts_no_concepts(self, service, mock_db):
        study = _make_study("step_2_draft")

        call_count = 0
        async def _exec(query):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=study)
            elif call_count == 1:
                result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=_exec)
        with pytest.raises(ValueError, match="No concepts found"):
            await service.lock_concepts(study.id, str(uuid.uuid4()), mock_db)

    @pytest.mark.asyncio
    async def test_lock_concepts_creates_step_version(self, service, mock_db):
        study = _make_study("step_2_draft")
        user_id = str(uuid.uuid4())
        concepts = [
            _make_concept(study_id=study.id, concept_index=1, status="approved"),
        ]

        call_count = 0
        async def _exec(query):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=study)
            elif call_count == 1:
                result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=concepts)))
            elif call_count == 2:
                result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=_exec)
        mock_db.refresh = AsyncMock(side_effect=lambda sv: (
            setattr(sv, 'locked_at', datetime.now(timezone.utc)),
            setattr(sv, 'version', 1),
        ))

        await service.lock_concepts(study.id, user_id, mock_db)
        # Verify db.add was called for the step version
        assert mock_db.add.called


# ═══════════════════════════════════════════════════════════════════════════
# 9. Prompt Loading Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPromptLoading:
    """Tests for loading and formatting concept prompts."""

    def test_concept_refiner_prompt_exists(self):
        svc = PromptService()
        template = svc.load_template("concept_refiner")
        assert len(template) > 0

    def test_concept_refiner_has_placeholders(self):
        svc = PromptService()
        template = svc.load_template("concept_refiner")
        assert "{category}" in template
        assert "{study_type}" in template
        assert "{competitor_brands}" in template
        assert "{raw_concept_json}" in template

    def test_concept_refiner_formatting(self):
        svc = PromptService()
        result = svc.format_prompt(
            "concept_refiner",
            category="snacks",
            study_type="concept_testing",
            competitor_brands="BrandA, BrandB",
            raw_concept_json='{"test": true}',
        )
        assert "snacks" in result
        assert "concept_testing" in result
        assert "BrandA, BrandB" in result

    def test_comparability_auditor_prompt_exists(self):
        svc = PromptService()
        template = svc.load_template("comparability_auditor")
        assert len(template) > 0

    def test_comparability_auditor_has_placeholder(self):
        svc = PromptService()
        template = svc.load_template("comparability_auditor")
        assert "{all_concepts_json}" in template

    def test_comparability_auditor_formatting(self):
        svc = PromptService()
        result = svc.format_prompt(
            "comparability_auditor",
            all_concepts_json='[{"concept_index": 1}]',
        )
        assert "concept_index" in result

    def test_concept_refiner_contains_rules(self):
        svc = PromptService()
        template = svc.load_template("concept_refiner")
        assert "consumer insight" in template.lower()
        assert "single-minded benefit" in template.lower()
        assert "rtb" in template.lower() or "reasons to believe" in template.lower()
        assert "credibility" in template.lower()

    def test_comparability_auditor_contains_criteria(self):
        svc = PromptService()
        template = svc.load_template("comparability_auditor")
        lower = template.lower()
        assert "level-of-finish" in lower or "level of finish" in lower
        assert "benefit clarity" in lower
        assert "price realism" in lower
        assert "loaded language" in lower
        assert "structural consistency" in lower
        assert "length balance" in lower


# ═══════════════════════════════════════════════════════════════════════════
# 10. Router Registration Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestRouterRegistration:
    """Tests for router endpoint definitions."""

    _PREFIX = "/api/v1/studies/{study_id}"

    def test_router_prefix(self):
        from app.routers.concepts import router
        assert router.prefix == "/api/v1/studies/{study_id}"

    def test_router_tags(self):
        from app.routers.concepts import router
        assert "Concepts" in router.tags

    def test_generate_endpoint_exists(self):
        from app.routers.concepts import router
        paths = [r.path for r in router.routes]
        assert f"{self._PREFIX}/steps/2/generate" in paths

    def test_update_concept_endpoint_exists(self):
        from app.routers.concepts import router
        paths = [r.path for r in router.routes]
        assert f"{self._PREFIX}/concepts/{{concept_id}}" in paths

    def test_refine_endpoint_exists(self):
        from app.routers.concepts import router
        paths = [r.path for r in router.routes]
        assert f"{self._PREFIX}/concepts/{{concept_id}}/refine" in paths

    def test_approve_endpoint_exists(self):
        from app.routers.concepts import router
        paths = [r.path for r in router.routes]
        assert f"{self._PREFIX}/concepts/{{concept_id}}/approve" in paths

    def test_comparability_check_endpoint_exists(self):
        from app.routers.concepts import router
        paths = [r.path for r in router.routes]
        assert f"{self._PREFIX}/concepts/comparability-check" in paths

    def test_render_endpoint_exists(self):
        from app.routers.concepts import router
        paths = [r.path for r in router.routes]
        assert f"{self._PREFIX}/concepts/{{concept_id}}/render" in paths

    def test_lock_endpoint_exists(self):
        from app.routers.concepts import router
        paths = [r.path for r in router.routes]
        assert f"{self._PREFIX}/steps/2/lock" in paths

    def test_endpoint_count(self):
        from app.routers.concepts import router
        # Should have 7 endpoints
        api_routes = [r for r in router.routes if hasattr(r, 'methods')]
        assert len(api_routes) == 7

    def test_generate_is_post(self):
        from app.routers.concepts import router
        for route in router.routes:
            if hasattr(route, 'path') and route.path.endswith("/steps/2/generate"):
                assert "POST" in route.methods

    def test_update_is_patch(self):
        from app.routers.concepts import router
        for route in router.routes:
            if hasattr(route, 'path') and route.path.endswith("/concepts/{concept_id}") and hasattr(route, 'methods'):
                assert "PATCH" in route.methods


# ═══════════════════════════════════════════════════════════════════════════
# 11. Default Template Components Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDefaultTemplateComponents:
    """Tests for the default template structure."""

    def _fresh(self):
        """Return a fresh deep copy to avoid cross-test mutation."""
        return copy.deepcopy(DEFAULT_TEMPLATE_COMPONENTS)

    def test_has_consumer_insight(self):
        assert "consumer_insight" in self._fresh()

    def test_has_product_name(self):
        assert "product_name" in self._fresh()

    def test_has_key_benefit(self):
        assert "key_benefit" in self._fresh()

    def test_has_reasons_to_believe(self):
        assert "reasons_to_believe" in self._fresh()

    def test_has_visual(self):
        assert "visual" in self._fresh()

    def test_has_price_format(self):
        assert "price_format" in self._fresh()

    def test_component_defaults_not_approved(self):
        t = self._fresh()
        for key in ["consumer_insight", "product_name", "key_benefit", "reasons_to_believe"]:
            assert t[key]["approved"] is False

    def test_component_defaults_raw_input_empty(self):
        t = self._fresh()
        for key in ["consumer_insight", "product_name", "key_benefit", "reasons_to_believe"]:
            assert t[key]["raw_input"] == ""

    def test_default_num_concepts(self):
        assert DEFAULT_NUM_CONCEPTS == 3
