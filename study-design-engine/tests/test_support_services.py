"""Tests for Support Services — audit, metrics, comments, versions, export — 40+ tests."""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from pathlib import Path

import pytest

from app.services.audit_service import AuditService
from app.services.metric_library_service import MetricLibraryService
from app.services.review_comment_service import ReviewCommentService
from app.services.version_history_service import VersionHistoryService
from app.services.study_export_service import StudyExportService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_audit_entry(study_id, action="step_1_generated", actor="system"):
    entry = MagicMock()
    entry.id = uuid.uuid4()
    entry.study_id = study_id
    entry.action = action
    entry.actor = actor
    entry.payload = {"version": 1}
    entry.created_at = datetime.now(timezone.utc)
    return entry


def make_comment(study_id, step=1, resolved=False):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.study_id = study_id
    c.step = step
    c.target_type = "step"
    c.target_id = None
    c.comment_text = "Looks good"
    c.resolved = resolved
    c.resolved_by = None
    c.created_at = datetime.now(timezone.utc)
    return c


def make_step_version(study_id, step=1, version=1, status="review"):
    sv = MagicMock()
    sv.id = uuid.uuid4()
    sv.study_id = study_id
    sv.step = step
    sv.version = version
    sv.status = status
    sv.content = {"study_type": "concept_testing"}
    sv.ai_rationale = {"source": "llm_generated"}
    sv.locked_at = None
    sv.locked_by = None
    sv.created_at = datetime.now(timezone.utc)
    return sv


def make_metric(metric_id="purchase_intent"):
    m = MagicMock()
    m.id = metric_id
    m.display_name = "Purchase Intent"
    m.category = "core_kpi"
    m.description = "Measures likelihood to purchase"
    m.applicable_study_types = ["concept_screening", "concept_testing"]
    m.default_scale = {"type": "likert_5", "options": []}
    m.benchmark_available = True
    m.created_at = datetime.now(timezone.utc)
    return m


def make_study(status="init"):
    study = MagicMock()
    study.id = uuid.uuid4()
    study.brand_id = uuid.uuid4()
    study.status = status
    study.question = "Which concept wins?"
    study.title = "Test Study"
    study.brand_name = "TestBrand"
    study.category = "snacks"
    study.context = {}
    study.study_metadata = {}
    study.created_at = datetime.now(timezone.utc)
    study.updated_at = datetime.now(timezone.utc)
    return study


# ===========================================================================
# AuditService tests
# ===========================================================================

class TestAuditServiceLogEvent:
    @pytest.mark.asyncio
    async def test_log_event_creates_record(self, mock_db_session):
        """log_event should create an AuditLog and return AuditLogEntry."""
        study_id = uuid.uuid4()
        result = await AuditService.log_event(
            study_id=study_id,
            action="step_1_generated",
            actor="system",
            payload={"version": 1},
            db=mock_db_session,
        )
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        assert result.study_id == study_id
        assert result.action == "step_1_generated"

    @pytest.mark.asyncio
    async def test_log_event_with_none_payload(self, mock_db_session):
        """log_event works with None payload."""
        result = await AuditService.log_event(
            study_id=uuid.uuid4(),
            action="test_action",
            actor="user",
            payload=None,
            db=mock_db_session,
        )
        assert result.payload is None

    @pytest.mark.asyncio
    async def test_log_event_with_complex_payload(self, mock_db_session):
        """log_event works with complex nested payload."""
        payload = {"version": 3, "edits": ["title", "metrics"], "nested": {"key": "val"}}
        result = await AuditService.log_event(
            study_id=uuid.uuid4(),
            action="step_1_edited",
            actor="user_123",
            payload=payload,
            db=mock_db_session,
        )
        assert result.payload == payload


class TestAuditServiceGetStudyAudit:
    @pytest.mark.asyncio
    async def test_get_study_audit_returns_entries(self, mock_db_session):
        """get_study_audit returns a list of entries."""
        study_id = uuid.uuid4()
        entries = [make_audit_entry(study_id), make_audit_entry(study_id, action="step_1_locked")]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = entries
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        results = await AuditService.get_study_audit(study_id, step=None, db=mock_db_session)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_study_audit_empty(self, mock_db_session):
        """get_study_audit returns empty list when no entries."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        results = await AuditService.get_study_audit(uuid.uuid4(), step=None, db=mock_db_session)
        assert results == []

    @pytest.mark.asyncio
    async def test_get_study_audit_filter_by_step(self, mock_db_session):
        """get_study_audit with step filter calls execute."""
        entries = [make_audit_entry(uuid.uuid4(), action="step_1_generated")]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = entries
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        results = await AuditService.get_study_audit(uuid.uuid4(), step=1, db=mock_db_session)
        assert len(results) == 1
        mock_db_session.execute.assert_called_once()


# ===========================================================================
# MetricLibraryService tests
# ===========================================================================

class TestMetricLibraryServiceList:
    @pytest.mark.asyncio
    async def test_list_metrics_returns_all(self, mock_db_session):
        """list_metrics without filter returns all metrics."""
        metrics = [make_metric("purchase_intent"), make_metric("uniqueness")]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = metrics
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        results = await MetricLibraryService.list_metrics(None, mock_db_session)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_metrics_with_study_type_filter(self, mock_db_session):
        """list_metrics with study_type filter calls execute."""
        metrics = [make_metric()]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = metrics
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        results = await MetricLibraryService.list_metrics("concept_testing", mock_db_session)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_list_metrics_empty(self, mock_db_session):
        """list_metrics returns empty when no metrics match."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        results = await MetricLibraryService.list_metrics("nonexistent", mock_db_session)
        assert results == []


class TestMetricLibraryServiceGet:
    @pytest.mark.asyncio
    async def test_get_metric_found(self, mock_db_session):
        """get_metric returns the metric when found."""
        m = make_metric()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = m
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        result = await MetricLibraryService.get_metric("purchase_intent", mock_db_session)
        assert result.id == "purchase_intent"

    @pytest.mark.asyncio
    async def test_get_metric_not_found(self, mock_db_session):
        """get_metric raises 404 when not found."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await MetricLibraryService.get_metric("nonexistent", mock_db_session)
        assert exc_info.value.status_code == 404


class TestMetricLibraryServiceCreate:
    @pytest.mark.asyncio
    async def test_create_metric_success(self, mock_db_session):
        """create_metric should add and commit."""
        from app.schemas.metric import MetricCreate
        data = MetricCreate(
            id="new_metric",
            display_name="New Metric",
            category="core_kpi",
            applicable_study_types=["concept_testing"],
            default_scale={"type": "likert_5", "options": []},
        )
        # First execute: check existing — not found
        existing_mock = MagicMock()
        existing_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=existing_mock)

        result = await MetricLibraryService.create_metric(data, mock_db_session)
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        assert result.id == "new_metric"

    @pytest.mark.asyncio
    async def test_create_metric_conflict(self, mock_db_session):
        """create_metric raises 409 when metric already exists."""
        from app.schemas.metric import MetricCreate
        data = MetricCreate(
            id="purchase_intent",
            display_name="Purchase Intent",
            category="core_kpi",
            applicable_study_types=["concept_testing"],
            default_scale={"type": "likert_5", "options": []},
        )
        existing_mock = MagicMock()
        existing_mock.scalar_one_or_none.return_value = make_metric()
        mock_db_session.execute = AsyncMock(return_value=existing_mock)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await MetricLibraryService.create_metric(data, mock_db_session)
        assert exc_info.value.status_code == 409


class TestMetricLibraryServiceUpdate:
    @pytest.mark.asyncio
    async def test_update_metric_success(self, mock_db_session):
        """update_metric applies changes to existing metric."""
        m = make_metric()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = m
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        result = await MetricLibraryService.update_metric(
            "purchase_intent",
            {"display_name": "Updated Name"},
            mock_db_session,
        )
        assert m.display_name == "Updated Name"
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_metric_not_found(self, mock_db_session):
        """update_metric raises 404 when not found."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await MetricLibraryService.update_metric("nonexistent", {"display_name": "X"}, mock_db_session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_metric_ignores_disallowed_fields(self, mock_db_session):
        """update_metric should not set id or other disallowed fields."""
        m = make_metric()
        original_id = m.id
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = m
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        await MetricLibraryService.update_metric(
            "purchase_intent",
            {"id": "hacked_id", "display_name": "Updated"},
            mock_db_session,
        )
        # id should NOT have been changed via setattr (it's not in allowed_fields)
        assert m.id == original_id


class TestMetricLibraryServiceDelete:
    @pytest.mark.asyncio
    async def test_delete_metric_success(self, mock_db_session):
        """delete_metric removes the metric."""
        m = make_metric()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = m
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        await MetricLibraryService.delete_metric("purchase_intent", mock_db_session)
        mock_db_session.delete.assert_called_once_with(m)
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_metric_not_found(self, mock_db_session):
        """delete_metric raises 404 when not found."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await MetricLibraryService.delete_metric("nonexistent", mock_db_session)
        assert exc_info.value.status_code == 404


class TestMetricLibraryServiceSeed:
    @pytest.mark.asyncio
    async def test_seed_metrics_loads_from_file(self, mock_db_session):
        """seed_metrics should read the seed file and upsert metrics."""
        # Mock the file check and reading
        seed_data = [
            {
                "id": "test_metric",
                "display_name": "Test",
                "category": "core_kpi",
                "description": "desc",
                "applicable_study_types": ["concept_testing"],
                "default_scale": {"type": "likert_5", "options": []},
                "benchmark_available": False,
            }
        ]

        # Each metric check returns None (new metric)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        with patch.object(MetricLibraryService, "SEED_FILE") as mock_path:
            mock_path.exists.return_value = True
            mock_path.read_text.return_value = json.dumps(seed_data)

            count = await MetricLibraryService.seed_metrics(mock_db_session)

        assert count == 1
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_seed_metrics_updates_existing(self, mock_db_session):
        """seed_metrics should update existing metrics."""
        seed_data = [
            {
                "id": "purchase_intent",
                "display_name": "Updated PI",
                "category": "core_kpi",
                "description": "desc",
                "applicable_study_types": ["concept_testing"],
                "default_scale": {"type": "likert_5", "options": []},
                "benchmark_available": True,
            }
        ]
        existing = make_metric()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        with patch.object(MetricLibraryService, "SEED_FILE") as mock_path:
            mock_path.exists.return_value = True
            mock_path.read_text.return_value = json.dumps(seed_data)

            count = await MetricLibraryService.seed_metrics(mock_db_session)

        assert count == 1
        assert existing.display_name == "Updated PI"

    @pytest.mark.asyncio
    async def test_seed_metrics_file_not_found(self, mock_db_session):
        """seed_metrics raises 500 when seed file is missing."""
        with patch.object(MetricLibraryService, "SEED_FILE") as mock_path:
            mock_path.exists.return_value = False

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await MetricLibraryService.seed_metrics(mock_db_session)
            assert exc_info.value.status_code == 500


# ===========================================================================
# ReviewCommentService tests
# ===========================================================================

class TestReviewCommentServiceAdd:
    @pytest.mark.asyncio
    async def test_add_comment_success(self, mock_db_session):
        """add_comment creates a comment and returns it."""
        from app.schemas.audit import ReviewCommentCreate
        study = make_study()
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study
        mock_db_session.execute = AsyncMock(return_value=study_result)

        data = ReviewCommentCreate(
            step=1,
            target_type="step",
            comment_text="Great brief!",
        )
        result = await ReviewCommentService.add_comment(study.id, data, mock_db_session)
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        assert result.comment_text == "Great brief!"
        assert result.resolved is False

    @pytest.mark.asyncio
    async def test_add_comment_study_not_found(self, mock_db_session):
        """add_comment raises 404 when study not found."""
        from app.schemas.audit import ReviewCommentCreate
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        data = ReviewCommentCreate(step=1, target_type="step", comment_text="test")
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await ReviewCommentService.add_comment(uuid.uuid4(), data, mock_db_session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_add_comment_with_target_id(self, mock_db_session):
        """add_comment can include target_id for specific element targeting."""
        from app.schemas.audit import ReviewCommentCreate
        study = make_study()
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study
        mock_db_session.execute = AsyncMock(return_value=study_result)

        data = ReviewCommentCreate(
            step=1,
            target_type="concept",
            target_id="concept_1",
            comment_text="Refine this concept",
        )
        result = await ReviewCommentService.add_comment(study.id, data, mock_db_session)
        assert result.target_type == "concept"
        assert result.target_id == "concept_1"


class TestReviewCommentServiceList:
    @pytest.mark.asyncio
    async def test_list_comments_all(self, mock_db_session):
        """list_comments without filters returns all."""
        study_id = uuid.uuid4()
        comments = [make_comment(study_id), make_comment(study_id, step=2)]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = comments
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        results = await ReviewCommentService.list_comments(study_id, None, None, mock_db_session)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_comments_filter_step(self, mock_db_session):
        """list_comments with step filter."""
        study_id = uuid.uuid4()
        comments = [make_comment(study_id, step=1)]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = comments
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        results = await ReviewCommentService.list_comments(study_id, step=1, resolved=None, db=mock_db_session)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_list_comments_filter_resolved(self, mock_db_session):
        """list_comments with resolved filter."""
        study_id = uuid.uuid4()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        results = await ReviewCommentService.list_comments(study_id, None, resolved=True, db=mock_db_session)
        assert results == []

    @pytest.mark.asyncio
    async def test_list_comments_filter_both(self, mock_db_session):
        """list_comments with both step and resolved filters."""
        study_id = uuid.uuid4()
        comments = [make_comment(study_id, step=1, resolved=False)]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = comments
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        results = await ReviewCommentService.list_comments(study_id, step=1, resolved=False, db=mock_db_session)
        assert len(results) == 1


class TestReviewCommentServiceResolve:
    @pytest.mark.asyncio
    async def test_resolve_comment_success(self, mock_db_session):
        """resolve_comment marks comment as resolved."""
        comment = make_comment(uuid.uuid4())
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = comment
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        result = await ReviewCommentService.resolve_comment(comment.id, "reviewer_1", mock_db_session)
        assert comment.resolved is True
        assert comment.resolved_by == "reviewer_1"
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_comment_not_found(self, mock_db_session):
        """resolve_comment raises 404 when comment not found."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await ReviewCommentService.resolve_comment(uuid.uuid4(), "user", mock_db_session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_resolve_comment_already_resolved(self, mock_db_session):
        """resolve_comment raises 409 when already resolved."""
        comment = make_comment(uuid.uuid4(), resolved=True)
        comment.resolved = True
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = comment
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await ReviewCommentService.resolve_comment(comment.id, "user", mock_db_session)
        assert exc_info.value.status_code == 409


# ===========================================================================
# VersionHistoryService tests
# ===========================================================================

class TestVersionHistoryServiceGetVersions:
    @pytest.mark.asyncio
    async def test_get_versions_all_steps(self, mock_db_session):
        """get_versions without step filter returns all versions."""
        study_id = uuid.uuid4()
        versions = [
            make_step_version(study_id, step=1, version=1),
            make_step_version(study_id, step=1, version=2),
            make_step_version(study_id, step=2, version=1),
        ]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = versions
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        results = await VersionHistoryService.get_versions(study_id, step=None, db=mock_db_session)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_get_versions_filter_step(self, mock_db_session):
        """get_versions with step filter returns only that step's versions."""
        study_id = uuid.uuid4()
        versions = [make_step_version(study_id, step=1, version=1)]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = versions
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        results = await VersionHistoryService.get_versions(study_id, step=1, db=mock_db_session)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_versions_empty(self, mock_db_session):
        """get_versions returns empty list when no versions exist."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        results = await VersionHistoryService.get_versions(uuid.uuid4(), step=1, db=mock_db_session)
        assert results == []


class TestVersionHistoryServiceGetVersion:
    @pytest.mark.asyncio
    async def test_get_version_found(self, mock_db_session):
        """get_version returns specific version when found."""
        study_id = uuid.uuid4()
        sv = make_step_version(study_id, step=1, version=2)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = sv
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        result = await VersionHistoryService.get_version(study_id, step=1, version=2, db=mock_db_session)
        assert result.step == 1
        assert result.version == 2

    @pytest.mark.asyncio
    async def test_get_version_not_found(self, mock_db_session):
        """get_version raises 404 when version does not exist."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await VersionHistoryService.get_version(uuid.uuid4(), step=1, version=99, db=mock_db_session)
        assert exc_info.value.status_code == 404


# ===========================================================================
# StudyExportService tests
# ===========================================================================

class TestStudyExportService:
    @pytest.mark.asyncio
    async def test_export_study_success(self, mock_db_session):
        """export_study assembles the full study payload."""
        study = make_study(status="step_1_locked")
        sv = make_step_version(study.id, step=1, version=1, status="locked")
        comment = make_comment(study.id)
        audit = make_audit_entry(study.id)

        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study

        versions_result = MagicMock()
        versions_result.scalars.return_value.all.return_value = [sv]

        comments_result = MagicMock()
        comments_result.scalars.return_value.all.return_value = [comment]

        audit_result = MagicMock()
        audit_result.scalars.return_value.all.return_value = [audit]

        mock_db_session.execute = AsyncMock(
            side_effect=[study_result, versions_result, comments_result, audit_result]
        )

        result = await StudyExportService.export_study(study.id, mock_db_session)

        assert "study" in result
        assert "steps" in result
        assert "all_versions" in result
        assert "comments" in result
        assert "audit_log" in result
        assert result["study"]["status"] == "step_1_locked"

    @pytest.mark.asyncio
    async def test_export_study_not_found(self, mock_db_session):
        """export_study raises 404 when study does not exist."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=result_mock)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await StudyExportService.export_study(uuid.uuid4(), mock_db_session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_export_study_empty_versions(self, mock_db_session):
        """export_study with no versions produces empty steps."""
        study = make_study()
        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study

        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[study_result, empty_result, empty_result, empty_result]
        )

        result = await StudyExportService.export_study(study.id, mock_db_session)
        assert result["steps"] == {}
        assert result["all_versions"] == []
        assert result["comments"] == []
        assert result["audit_log"] == []

    @pytest.mark.asyncio
    async def test_export_study_multiple_versions(self, mock_db_session):
        """export_study keeps only latest version per step in steps dict."""
        study = make_study(status="step_1_review")
        sv1 = make_step_version(study.id, step=1, version=2, status="review")
        sv2 = make_step_version(study.id, step=1, version=1, status="draft")

        study_result = MagicMock()
        study_result.scalar_one_or_none.return_value = study

        versions_result = MagicMock()
        # Ordered by version desc, so sv1 (v2) comes first
        versions_result.scalars.return_value.all.return_value = [sv1, sv2]

        empty = MagicMock()
        empty.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[study_result, versions_result, empty, empty]
        )

        result = await StudyExportService.export_study(study.id, mock_db_session)
        # steps dict should only have the latest (first encountered in desc order)
        assert 1 in result["steps"]
        assert result["steps"][1]["version"] == 2
        # all_versions should have both
        assert len(result["all_versions"]) == 2
