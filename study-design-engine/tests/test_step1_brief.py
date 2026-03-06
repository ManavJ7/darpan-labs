"""Tests for Study Brief (Step 1) service and router — 35+ tests."""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.study_brief_service import StudyBriefService
from app.services.state_machine import StudyStateMachine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_study(status="init", brand_name="TestBrand", category="snacks", question="Which concept wins?"):
    """Create a mock Study object."""
    study = MagicMock()
    study.id = uuid.uuid4()
    study.brand_id = uuid.uuid4()
    study.status = status
    study.question = question
    study.title = None
    study.brand_name = brand_name
    study.category = category
    study.context = {"revenue_range": "$10M-$50M", "previous_studies": []}
    study.study_metadata = {}
    study.created_at = datetime.now(timezone.utc)
    study.updated_at = datetime.now(timezone.utc)
    return study


def make_step_version(study_id, step=1, version=1, status="review", content=None):
    """Create a mock StepVersion object."""
    sv = MagicMock()
    sv.id = uuid.uuid4()
    sv.study_id = study_id
    sv.step = step
    sv.version = version
    sv.status = status
    sv.content = content or {
        "study_type": "concept_testing",
        "study_type_confidence": 0.92,
        "recommended_title": "Test Study",
        "recommended_metrics": ["purchase_intent", "uniqueness"],
        "recommended_audience": {"age": "18-45"},
        "methodology_family": "sequential_monadic",
        "methodology_rationale": "Best for multi-concept testing",
        "clarification_questions": [],
        "flags": [],
    }
    sv.ai_rationale = {"source": "llm_generated"}
    sv.locked_at = None
    sv.locked_by = None
    sv.created_at = datetime.now(timezone.utc)
    return sv


def make_metric(metric_id="purchase_intent"):
    """Create a mock MetricLibrary object."""
    m = MagicMock()
    m.id = metric_id
    m.display_name = "Purchase Intent"
    m.category = "core_kpi"
    m.description = "Measures likelihood to purchase"
    m.applicable_study_types = ["concept_screening", "concept_testing"]
    m.default_scale = {"type": "likert_5", "options": []}
    m.benchmark_available = True
    return m


BRIEF_JSON = {
    "study_type": "concept_testing",
    "study_type_confidence": 0.92,
    "recommended_title": "Snack Concept Test",
    "recommended_metrics": ["purchase_intent", "uniqueness"],
    "recommended_audience": {"age": "18-45", "geography": "urban"},
    "methodology_family": "sequential_monadic",
    "methodology_rationale": "Best for multi-concept testing",
    "clarification_questions": [],
    "flags": [],
}


def _setup_db_for_generate(mock_db, study, metrics=None):
    """Configure mock_db.execute to return study then metrics then version count."""
    if metrics is None:
        metrics = [make_metric("purchase_intent"), make_metric("uniqueness")]

    study_result = MagicMock()
    study_result.scalar_one_or_none.return_value = study

    metrics_result = MagicMock()
    metrics_result.scalars.return_value.all.return_value = metrics

    version_count_result = MagicMock()
    version_count_result.scalar.return_value = 0

    # For audit log event — study lookup, then the insert returns
    audit_result = MagicMock()

    mock_db.execute = AsyncMock(
        side_effect=[study_result, metrics_result, version_count_result, audit_result]
    )


def _setup_db_for_edit(mock_db, study, latest_sv, next_version=2):
    """Configure mock_db for edit_brief."""
    study_result = MagicMock()
    study_result.scalar_one_or_none.return_value = study

    latest_result = MagicMock()
    latest_result.scalar_one_or_none.return_value = latest_sv

    version_count_result = MagicMock()
    version_count_result.scalar.return_value = latest_sv.version

    audit_result = MagicMock()

    mock_db.execute = AsyncMock(
        side_effect=[study_result, latest_result, version_count_result, audit_result]
    )


def _setup_db_for_lock(mock_db, study, latest_sv):
    """Configure mock_db for lock_brief."""
    study_result = MagicMock()
    study_result.scalar_one_or_none.return_value = study

    latest_result = MagicMock()
    latest_result.scalar_one_or_none.return_value = latest_sv

    audit_result = MagicMock()

    mock_db.execute = AsyncMock(
        side_effect=[study_result, latest_result, audit_result]
    )


# ---------------------------------------------------------------------------
# generate_brief tests
# ---------------------------------------------------------------------------

class TestGenerateBrief:
    @pytest.mark.asyncio
    async def test_generate_brief_from_init_status(self, mock_db_session, mock_llm_client):
        """Generate brief when study is in init status."""
        study = make_study(status="init")
        _setup_db_for_generate(mock_db_session, study)
        mock_llm_client.generate_json = AsyncMock(return_value=BRIEF_JSON)

        service = StudyBriefService(llm_client=mock_llm_client)
        result = await service.generate_brief(study.id, mock_db_session)

        assert result.step == 1
        assert result.version == 1
        assert result.content == BRIEF_JSON
        assert result.status == "review"
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_generate_brief_from_step_1_draft(self, mock_db_session, mock_llm_client):
        """Generate brief when study is in step_1_draft."""
        study = make_study(status="step_1_draft")
        _setup_db_for_generate(mock_db_session, study)
        mock_llm_client.generate_json = AsyncMock(return_value=BRIEF_JSON)

        service = StudyBriefService(llm_client=mock_llm_client)
        result = await service.generate_brief(study.id, mock_db_session)

        assert result.step == 1
        assert result.content["study_type"] == "concept_testing"

    @pytest.mark.asyncio
    async def test_generate_brief_transitions_status_to_review(self, mock_db_session, mock_llm_client):
        """Study should transition from init -> step_1_draft -> step_1_review."""
        study = make_study(status="init")
        _setup_db_for_generate(mock_db_session, study)
        mock_llm_client.generate_json = AsyncMock(return_value=BRIEF_JSON)

        service = StudyBriefService(llm_client=mock_llm_client)
        await service.generate_brief(study.id, mock_db_session)

        assert study.status == "step_1_review"

    @pytest.mark.asyncio
    async def test_generate_brief_rejects_locked_study(self, mock_db_session, mock_llm_client):
        """Cannot generate when study is step_1_locked."""
        study = make_study(status="step_1_locked")
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study
        mock_db_session.execute = AsyncMock(return_value=study_result)

        service = StudyBriefService(llm_client=mock_llm_client)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_brief(study.id, mock_db_session)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_generate_brief_rejects_review_status(self, mock_db_session, mock_llm_client):
        """Cannot generate when study is already in step_1_review."""
        study = make_study(status="step_1_review")
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study
        mock_db_session.execute = AsyncMock(return_value=study_result)

        service = StudyBriefService(llm_client=mock_llm_client)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_brief(study.id, mock_db_session)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_generate_brief_rejects_step_2_status(self, mock_db_session, mock_llm_client):
        """Cannot generate step 1 when study is in step_2_draft."""
        study = make_study(status="step_2_draft")
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study
        mock_db_session.execute = AsyncMock(return_value=study_result)

        service = StudyBriefService(llm_client=mock_llm_client)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_brief(study.id, mock_db_session)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_generate_brief_study_not_found(self, mock_db_session, mock_llm_client):
        """404 when study does not exist."""
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=study_result)

        service = StudyBriefService(llm_client=mock_llm_client)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_brief(uuid.uuid4(), mock_db_session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_brief_llm_failure(self, mock_db_session, mock_llm_client):
        """502 when LLM call fails."""
        study = make_study(status="init")
        metrics = [make_metric()]
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study
        metrics_result = MagicMock()
        metrics_result.scalars.return_value.all.return_value = metrics

        mock_db_session.execute = AsyncMock(
            side_effect=[study_result, metrics_result]
        )
        mock_llm_client.generate_json = AsyncMock(side_effect=RuntimeError("LLM down"))

        service = StudyBriefService(llm_client=mock_llm_client)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_brief(study.id, mock_db_session)
        assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_generate_brief_increments_version(self, mock_db_session, mock_llm_client):
        """Version should increment from existing max."""
        study = make_study(status="step_1_draft")
        metrics = [make_metric()]
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study
        metrics_result = MagicMock()
        metrics_result.scalars.return_value.all.return_value = metrics
        version_count_result = MagicMock()
        version_count_result.scalar.return_value = 3  # existing max version is 3
        audit_result = MagicMock()

        mock_db_session.execute = AsyncMock(
            side_effect=[study_result, metrics_result, version_count_result, audit_result]
        )
        mock_llm_client.generate_json = AsyncMock(return_value=BRIEF_JSON)

        service = StudyBriefService(llm_client=mock_llm_client)
        result = await service.generate_brief(study.id, mock_db_session)

        assert result.version == 4

    @pytest.mark.asyncio
    async def test_generate_brief_uses_prompt_template(self, mock_db_session, mock_llm_client):
        """Verify the prompt service is called with correct template name."""
        study = make_study(status="init")
        _setup_db_for_generate(mock_db_session, study)
        mock_llm_client.generate_json = AsyncMock(return_value=BRIEF_JSON)

        prompt_svc = MagicMock()
        prompt_svc.format_prompt = MagicMock(return_value="formatted prompt")

        service = StudyBriefService(llm_client=mock_llm_client, prompt_service=prompt_svc)
        await service.generate_brief(study.id, mock_db_session)

        prompt_svc.format_prompt.assert_called_once()
        call_args = prompt_svc.format_prompt.call_args
        assert call_args[0][0] == "study_brief_generator"

    @pytest.mark.asyncio
    async def test_generate_brief_passes_brand_context(self, mock_db_session, mock_llm_client):
        """Verify brand context is passed to prompt."""
        study = make_study(status="init", brand_name="Acme", category="beverages")
        study.context = {"revenue_range": "$100M+", "previous_studies": ["study_a"]}
        _setup_db_for_generate(mock_db_session, study)
        mock_llm_client.generate_json = AsyncMock(return_value=BRIEF_JSON)

        prompt_svc = MagicMock()
        prompt_svc.format_prompt = MagicMock(return_value="formatted")

        service = StudyBriefService(llm_client=mock_llm_client, prompt_service=prompt_svc)
        await service.generate_brief(study.id, mock_db_session)

        kwargs = prompt_svc.format_prompt.call_args[1]
        assert kwargs["brand_name"] == "Acme"
        assert kwargs["category"] == "beverages"
        assert kwargs["revenue_range"] == "$100M+"

    @pytest.mark.asyncio
    async def test_generate_brief_handles_missing_context(self, mock_db_session, mock_llm_client):
        """When context is None or empty, defaults should be used."""
        study = make_study(status="init")
        study.context = None
        _setup_db_for_generate(mock_db_session, study)
        mock_llm_client.generate_json = AsyncMock(return_value=BRIEF_JSON)

        prompt_svc = MagicMock()
        prompt_svc.format_prompt = MagicMock(return_value="formatted")

        service = StudyBriefService(llm_client=mock_llm_client, prompt_service=prompt_svc)
        await service.generate_brief(study.id, mock_db_session)

        kwargs = prompt_svc.format_prompt.call_args[1]
        assert kwargs["revenue_range"] == "Not specified"

    @pytest.mark.asyncio
    async def test_generate_brief_handles_missing_brand_name(self, mock_db_session, mock_llm_client):
        """When brand_name is None, 'Unknown' should be used."""
        study = make_study(status="init", brand_name=None)
        _setup_db_for_generate(mock_db_session, study)
        mock_llm_client.generate_json = AsyncMock(return_value=BRIEF_JSON)

        prompt_svc = MagicMock()
        prompt_svc.format_prompt = MagicMock(return_value="formatted")

        service = StudyBriefService(llm_client=mock_llm_client, prompt_service=prompt_svc)
        await service.generate_brief(study.id, mock_db_session)

        kwargs = prompt_svc.format_prompt.call_args[1]
        assert kwargs["brand_name"] == "Unknown"

    @pytest.mark.asyncio
    async def test_generate_brief_stores_ai_rationale(self, mock_db_session, mock_llm_client):
        """ai_rationale should contain source and model info."""
        study = make_study(status="init")
        _setup_db_for_generate(mock_db_session, study)
        mock_llm_client.generate_json = AsyncMock(return_value=BRIEF_JSON)

        service = StudyBriefService(llm_client=mock_llm_client)
        result = await service.generate_brief(study.id, mock_db_session)

        assert result.ai_rationale is not None
        assert result.ai_rationale["source"] == "llm_generated"


# ---------------------------------------------------------------------------
# edit_brief tests
# ---------------------------------------------------------------------------

class TestEditBrief:
    @pytest.mark.asyncio
    async def test_edit_brief_creates_new_version(self, mock_db_session, mock_llm_client):
        """Editing should create a new version with merged content."""
        study = make_study(status="step_1_review")
        sv = make_step_version(study.id, version=1)
        _setup_db_for_edit(mock_db_session, study, sv)

        service = StudyBriefService(llm_client=mock_llm_client)
        result = await service.edit_brief(
            study.id,
            {"recommended_title": "Updated Title"},
            mock_db_session,
        )

        assert result.version == 2
        assert result.content["recommended_title"] == "Updated Title"
        # Other fields preserved
        assert result.content["study_type"] == "concept_testing"

    @pytest.mark.asyncio
    async def test_edit_brief_rejects_locked_step(self, mock_db_session, mock_llm_client):
        """Cannot edit when step 1 is locked."""
        study = make_study(status="step_1_locked")
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study
        mock_db_session.execute = AsyncMock(return_value=study_result)

        service = StudyBriefService(llm_client=mock_llm_client)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.edit_brief(study.id, {"title": "New"}, mock_db_session)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_edit_brief_rejects_when_study_past_step1(self, mock_db_session, mock_llm_client):
        """Cannot edit step 1 when study is on step 3."""
        study = make_study(status="step_3_draft")
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study
        mock_db_session.execute = AsyncMock(return_value=study_result)

        service = StudyBriefService(llm_client=mock_llm_client)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.edit_brief(study.id, {"title": "New"}, mock_db_session)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_edit_brief_404_when_no_existing_version(self, mock_db_session, mock_llm_client):
        """404 when there is no existing step 1 version to base edits on."""
        study = make_study(status="step_1_review")
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study
        latest_result = MagicMock()
        latest_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(side_effect=[study_result, latest_result])

        service = StudyBriefService(llm_client=mock_llm_client)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.edit_brief(study.id, {"title": "New"}, mock_db_session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_edit_brief_study_not_found(self, mock_db_session, mock_llm_client):
        """404 when study does not exist."""
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=study_result)

        service = StudyBriefService(llm_client=mock_llm_client)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.edit_brief(uuid.uuid4(), {"title": "New"}, mock_db_session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_edit_brief_preserves_existing_content(self, mock_db_session, mock_llm_client):
        """Fields not in edits should remain unchanged."""
        study = make_study(status="step_1_review")
        original_content = {
            "study_type": "concept_testing",
            "recommended_title": "Original Title",
            "recommended_metrics": ["purchase_intent"],
            "methodology_family": "monadic",
        }
        sv = make_step_version(study.id, version=1, content=original_content)
        _setup_db_for_edit(mock_db_session, study, sv)

        service = StudyBriefService(llm_client=mock_llm_client)
        result = await service.edit_brief(
            study.id,
            {"recommended_title": "New Title"},
            mock_db_session,
        )

        assert result.content["study_type"] == "concept_testing"
        assert result.content["methodology_family"] == "monadic"
        assert result.content["recommended_title"] == "New Title"

    @pytest.mark.asyncio
    async def test_edit_brief_records_ai_rationale(self, mock_db_session, mock_llm_client):
        """ai_rationale should note manual_edit source and edited fields."""
        study = make_study(status="step_1_review")
        sv = make_step_version(study.id, version=1)
        _setup_db_for_edit(mock_db_session, study, sv)

        service = StudyBriefService(llm_client=mock_llm_client)
        result = await service.edit_brief(
            study.id,
            {"recommended_title": "Edited"},
            mock_db_session,
        )

        assert result.ai_rationale["source"] == "manual_edit"
        assert "recommended_title" in result.ai_rationale["edits_applied"]

    @pytest.mark.asyncio
    async def test_edit_brief_transitions_from_draft_to_review(self, mock_db_session, mock_llm_client):
        """Editing in step_1_draft should transition to step_1_review."""
        study = make_study(status="step_1_draft")
        sv = make_step_version(study.id, version=1)
        _setup_db_for_edit(mock_db_session, study, sv)

        service = StudyBriefService(llm_client=mock_llm_client)
        await service.edit_brief(study.id, {"title": "X"}, mock_db_session)

        assert study.status == "step_1_review"

    @pytest.mark.asyncio
    async def test_edit_brief_multiple_edits(self, mock_db_session, mock_llm_client):
        """Applying multiple edits at once should merge all of them."""
        study = make_study(status="step_1_review")
        sv = make_step_version(study.id, version=1)
        _setup_db_for_edit(mock_db_session, study, sv)

        service = StudyBriefService(llm_client=mock_llm_client)
        result = await service.edit_brief(
            study.id,
            {
                "recommended_title": "New Title",
                "study_type": "brand_positioning",
                "methodology_family": "perceptual_mapping",
            },
            mock_db_session,
        )

        assert result.content["recommended_title"] == "New Title"
        assert result.content["study_type"] == "brand_positioning"
        assert result.content["methodology_family"] == "perceptual_mapping"


# ---------------------------------------------------------------------------
# lock_brief tests
# ---------------------------------------------------------------------------

class TestLockBrief:
    @pytest.mark.asyncio
    async def test_lock_brief_success(self, mock_db_session, mock_llm_client):
        """Lock step 1 when study is in step_1_review."""
        study = make_study(status="step_1_review")
        sv = make_step_version(study.id, version=2)
        _setup_db_for_lock(mock_db_session, study, sv)

        user_id = str(uuid.uuid4())
        service = StudyBriefService(llm_client=mock_llm_client)
        result = await service.lock_brief(study.id, user_id, mock_db_session)

        assert result.status == "locked"
        assert study.status == "step_1_locked"

    @pytest.mark.asyncio
    async def test_lock_brief_sets_locked_at(self, mock_db_session, mock_llm_client):
        """locked_at should be set after locking."""
        study = make_study(status="step_1_review")
        sv = make_step_version(study.id)
        _setup_db_for_lock(mock_db_session, study, sv)

        user_id = str(uuid.uuid4())
        service = StudyBriefService(llm_client=mock_llm_client)
        await service.lock_brief(study.id, user_id, mock_db_session)

        assert sv.locked_at is not None

    @pytest.mark.asyncio
    async def test_lock_brief_sets_locked_by(self, mock_db_session, mock_llm_client):
        """locked_by should be set to user_id."""
        study = make_study(status="step_1_review")
        sv = make_step_version(study.id)
        _setup_db_for_lock(mock_db_session, study, sv)

        user_id = str(uuid.uuid4())
        service = StudyBriefService(llm_client=mock_llm_client)
        await service.lock_brief(study.id, user_id, mock_db_session)

        assert sv.locked_by == uuid.UUID(user_id)

    @pytest.mark.asyncio
    async def test_lock_brief_rejects_draft_status(self, mock_db_session, mock_llm_client):
        """Cannot lock when study is in step_1_draft."""
        study = make_study(status="step_1_draft")
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study
        mock_db_session.execute = AsyncMock(return_value=study_result)

        service = StudyBriefService(llm_client=mock_llm_client)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.lock_brief(study.id, str(uuid.uuid4()), mock_db_session)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_lock_brief_rejects_init_status(self, mock_db_session, mock_llm_client):
        """Cannot lock when study is in init."""
        study = make_study(status="init")
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study
        mock_db_session.execute = AsyncMock(return_value=study_result)

        service = StudyBriefService(llm_client=mock_llm_client)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.lock_brief(study.id, str(uuid.uuid4()), mock_db_session)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_lock_brief_rejects_already_locked(self, mock_db_session, mock_llm_client):
        """Cannot lock when already locked."""
        study = make_study(status="step_1_locked")
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study
        mock_db_session.execute = AsyncMock(return_value=study_result)

        service = StudyBriefService(llm_client=mock_llm_client)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.lock_brief(study.id, str(uuid.uuid4()), mock_db_session)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_lock_brief_study_not_found(self, mock_db_session, mock_llm_client):
        """404 when study does not exist."""
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=study_result)

        service = StudyBriefService(llm_client=mock_llm_client)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.lock_brief(uuid.uuid4(), str(uuid.uuid4()), mock_db_session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_lock_brief_no_version_found(self, mock_db_session, mock_llm_client):
        """404 when no step version exists to lock."""
        study = make_study(status="step_1_review")
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study
        latest_result = MagicMock()
        latest_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(side_effect=[study_result, latest_result])

        service = StudyBriefService(llm_client=mock_llm_client)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.lock_brief(study.id, str(uuid.uuid4()), mock_db_session)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Helper method tests
# ---------------------------------------------------------------------------

class TestHelperMethods:
    @pytest.mark.asyncio
    async def test_get_study_returns_study(self, mock_db_session):
        """_get_study returns the study when found."""
        study = make_study()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = study
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        found = await StudyBriefService._get_study(study.id, mock_db_session)
        assert found.id == study.id

    @pytest.mark.asyncio
    async def test_get_study_raises_404(self, mock_db_session):
        """_get_study raises 404 when not found."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await StudyBriefService._get_study(uuid.uuid4(), mock_db_session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_next_version_first(self, mock_db_session):
        """First version should be 1 when no existing versions."""
        result_mock = MagicMock()
        result_mock.scalar.return_value = 0
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        v = await StudyBriefService._next_version(uuid.uuid4(), step=1, db=mock_db_session)
        assert v == 1

    @pytest.mark.asyncio
    async def test_next_version_increment(self, mock_db_session):
        """Next version should be max + 1."""
        result_mock = MagicMock()
        result_mock.scalar.return_value = 5
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        v = await StudyBriefService._next_version(uuid.uuid4(), step=1, db=mock_db_session)
        assert v == 6
