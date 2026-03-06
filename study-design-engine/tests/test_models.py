"""Tests for database models — 35+ tests."""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect

from app.database import Base
from app.models.study import Study, StepVersion
from app.models.concept import Concept
from app.models.audit import ReviewComment, AuditLog
from app.models.metric import MetricLibrary


# ─── Study Model ───

class TestStudyModel:
    def test_study_tablename(self):
        assert Study.__tablename__ == "studies"

    def test_study_has_id_column(self):
        cols = {c.name for c in Study.__table__.columns}
        assert "id" in cols

    def test_study_has_brand_id_column(self):
        cols = {c.name for c in Study.__table__.columns}
        assert "brand_id" in cols

    def test_study_has_status_column(self):
        cols = {c.name for c in Study.__table__.columns}
        assert "status" in cols

    def test_study_has_question_column(self):
        cols = {c.name for c in Study.__table__.columns}
        assert "question" in cols

    def test_study_has_title_column(self):
        cols = {c.name for c in Study.__table__.columns}
        assert "title" in cols

    def test_study_has_brand_name_column(self):
        cols = {c.name for c in Study.__table__.columns}
        assert "brand_name" in cols

    def test_study_has_category_column(self):
        cols = {c.name for c in Study.__table__.columns}
        assert "category" in cols

    def test_study_has_context_column(self):
        cols = {c.name for c in Study.__table__.columns}
        assert "context" in cols

    def test_study_has_study_metadata_column(self):
        cols = {c.name for c in Study.__table__.columns}
        assert "study_metadata" in cols

    def test_study_has_created_at_column(self):
        cols = {c.name for c in Study.__table__.columns}
        assert "created_at" in cols

    def test_study_has_updated_at_column(self):
        cols = {c.name for c in Study.__table__.columns}
        assert "updated_at" in cols

    def test_study_status_default(self):
        col = Study.__table__.columns["status"]
        assert col.default.arg == "init"

    def test_study_primary_key_is_id(self):
        pk_cols = [c.name for c in Study.__table__.primary_key.columns]
        assert pk_cols == ["id"]

    def test_study_id_is_uuid_type(self):
        col = Study.__table__.columns["id"]
        assert "UUID" in str(col.type)


# ─── StepVersion Model ───

class TestStepVersionModel:
    def test_step_version_tablename(self):
        assert StepVersion.__tablename__ == "step_versions"

    def test_step_version_has_all_columns(self):
        cols = {c.name for c in StepVersion.__table__.columns}
        expected = {"id", "study_id", "step", "version", "status", "content",
                    "ai_rationale", "locked_at", "locked_by", "created_at"}
        assert expected.issubset(cols)

    def test_step_version_status_default(self):
        col = StepVersion.__table__.columns["status"]
        assert col.default.arg == "draft"

    def test_step_version_version_default(self):
        col = StepVersion.__table__.columns["version"]
        assert col.default.arg == 1

    def test_step_version_has_unique_constraint(self):
        constraints = [c for c in StepVersion.__table__.constraints
                       if hasattr(c, 'columns') and len(c.columns) > 1]
        # Should have unique constraint on (study_id, step, version)
        found = False
        for c in constraints:
            col_names = {col.name for col in c.columns}
            if col_names == {"study_id", "step", "version"}:
                found = True
        assert found

    def test_step_version_foreign_key(self):
        col = StepVersion.__table__.columns["study_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert "studies.id" in str(fks[0])


# ─── Concept Model ───

class TestConceptModel:
    def test_concept_tablename(self):
        assert Concept.__tablename__ == "concepts"

    def test_concept_has_all_columns(self):
        cols = {c.name for c in Concept.__table__.columns}
        expected = {"id", "study_id", "concept_index", "version", "status",
                    "components", "comparability_flags", "image_url", "image_version",
                    "created_at", "updated_at"}
        assert expected.issubset(cols)

    def test_concept_status_default(self):
        col = Concept.__table__.columns["status"]
        assert col.default.arg == "raw"

    def test_concept_has_unique_constraint(self):
        constraints = [c for c in Concept.__table__.constraints
                       if hasattr(c, 'columns') and len(c.columns) > 1]
        found = False
        for c in constraints:
            col_names = {col.name for col in c.columns}
            if col_names == {"study_id", "concept_index", "version"}:
                found = True
        assert found

    def test_concept_foreign_key(self):
        col = Concept.__table__.columns["study_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert "studies.id" in str(fks[0])

    def test_concept_image_version_default(self):
        col = Concept.__table__.columns["image_version"]
        assert col.default.arg == 0


# ─── ReviewComment Model ───

class TestReviewCommentModel:
    def test_review_comment_tablename(self):
        assert ReviewComment.__tablename__ == "review_comments"

    def test_review_comment_has_all_columns(self):
        cols = {c.name for c in ReviewComment.__table__.columns}
        expected = {"id", "study_id", "step", "target_type", "target_id",
                    "comment_text", "resolved", "resolved_by", "created_at"}
        assert expected.issubset(cols)

    def test_review_comment_resolved_default(self):
        col = ReviewComment.__table__.columns["resolved"]
        assert col.default.arg is False

    def test_review_comment_foreign_key(self):
        col = ReviewComment.__table__.columns["study_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1


# ─── AuditLog Model ───

class TestAuditLogModel:
    def test_audit_log_tablename(self):
        assert AuditLog.__tablename__ == "audit_log"

    def test_audit_log_has_all_columns(self):
        cols = {c.name for c in AuditLog.__table__.columns}
        expected = {"id", "study_id", "action", "actor", "payload", "created_at"}
        assert expected.issubset(cols)

    def test_audit_log_foreign_key(self):
        col = AuditLog.__table__.columns["study_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1


# ─── MetricLibrary Model ───

class TestMetricLibraryModel:
    def test_metric_library_tablename(self):
        assert MetricLibrary.__tablename__ == "metric_library"

    def test_metric_library_has_all_columns(self):
        cols = {c.name for c in MetricLibrary.__table__.columns}
        expected = {"id", "display_name", "category", "description",
                    "applicable_study_types", "default_scale", "benchmark_available",
                    "created_at"}
        assert expected.issubset(cols)

    def test_metric_library_primary_key_is_string_id(self):
        col = MetricLibrary.__table__.columns["id"]
        assert "VARCHAR" in str(col.type) or "String" in str(col.type).title()

    def test_metric_library_benchmark_default(self):
        col = MetricLibrary.__table__.columns["benchmark_available"]
        assert col.default.arg is False


# ─── Base / Meta ───

class TestBaseMeta:
    def test_all_models_use_same_base(self):
        assert Study.__class__.__bases__[0] == StepVersion.__class__.__bases__[0]

    def test_total_tables(self):
        table_names = set(Base.metadata.tables.keys())
        expected = {"studies", "step_versions", "concepts", "review_comments",
                    "audit_log", "metric_library"}
        assert expected.issubset(table_names)
