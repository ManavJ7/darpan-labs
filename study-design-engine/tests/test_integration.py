"""Integration tests — verify all routers wired, endpoint patterns, and cross-step logic.

Target: 35+ tests covering router wiring, route existence, state machine enforcement,
and end-to-end flow patterns (all with mocked DB/LLM).
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.state_machine import StudyStateMachine


# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────

def _routes() -> list[str]:
    """Collect all route paths registered on the FastAPI app."""
    return [getattr(r, "path", "") for r in app.routes]


def _route_methods() -> dict[str, set[str]]:
    """Map route path → HTTP methods."""
    out: dict[str, set[str]] = {}
    for r in app.routes:
        if hasattr(r, "methods") and hasattr(r, "path"):
            out[r.path] = r.methods
    return out


# ────────────────────────────────────────────────────────────
# Router Wiring Tests — verify all Phase 2 routers are included
# ────────────────────────────────────────────────────────────

class TestRouterWiring:
    """All Phase 2 routers should be wired into the main app."""

    # -- Step 1 routes (studies router) --
    def test_step1_generate_route_exists(self):
        assert "/api/v1/studies/{study_id}/steps/1/generate" in _routes()

    def test_step1_edit_route_exists(self):
        assert "/api/v1/studies/{study_id}/steps/1" in _routes()

    def test_step1_lock_route_exists(self):
        assert "/api/v1/studies/{study_id}/steps/1/lock" in _routes()

    # -- Metrics routes --
    def test_metrics_list_route_exists(self):
        assert "/api/v1/metrics/" in _routes() or "/api/v1/metrics" in _routes()

    def test_metrics_seed_route_exists(self):
        assert "/api/v1/metrics/seed" in _routes()

    # -- Audit routes --
    def test_audit_route_exists(self):
        assert "/api/v1/studies/{study_id}/audit-log/" in _routes() or \
               "/api/v1/studies/{study_id}/audit-log" in _routes()

    # -- Comments routes --
    def test_comments_list_route_exists(self):
        assert "/api/v1/studies/{study_id}/comments/" in _routes() or \
               "/api/v1/studies/{study_id}/comments" in _routes()

    def test_comments_resolve_route_exists(self):
        assert "/api/v1/studies/{study_id}/comments/{comment_id}/resolve" in _routes()

    # -- Versions routes --
    def test_versions_list_route_exists(self):
        assert "/api/v1/studies/{study_id}/steps/{step}/versions" in _routes()

    def test_versions_get_route_exists(self):
        assert "/api/v1/studies/{study_id}/steps/{step}/versions/{version}" in _routes()

    # -- Export route --
    def test_export_route_exists(self):
        assert "/api/v1/studies/{study_id}/export" in _routes()

    # -- Step 2 routes (concepts router) --
    def test_step2_generate_route_exists(self):
        assert "/api/v1/studies/{study_id}/steps/2/generate" in _routes()

    def test_concept_update_route_exists(self):
        assert "/api/v1/studies/{study_id}/concepts/{concept_id}" in _routes()

    def test_concept_refine_route_exists(self):
        assert "/api/v1/studies/{study_id}/concepts/{concept_id}/refine" in _routes()

    def test_concept_approve_route_exists(self):
        assert "/api/v1/studies/{study_id}/concepts/{concept_id}/approve" in _routes()

    def test_comparability_check_route_exists(self):
        assert "/api/v1/studies/{study_id}/concepts/comparability-check" in _routes()

    def test_concept_render_route_exists(self):
        assert "/api/v1/studies/{study_id}/concepts/{concept_id}/render" in _routes()

    def test_step2_lock_route_exists(self):
        assert "/api/v1/studies/{study_id}/steps/2/lock" in _routes()

    # -- Step 3 routes (research design router) --
    def test_step3_generate_route_exists(self):
        assert "/api/v1/studies/{study_id}/steps/3/generate" in _routes()

    def test_step3_edit_route_exists(self):
        # The PATCH route for step 3
        rm = _route_methods()
        assert "/api/v1/studies/{study_id}/steps/3" in rm
        assert "PATCH" in rm["/api/v1/studies/{study_id}/steps/3"]

    def test_step3_lock_route_exists(self):
        assert "/api/v1/studies/{study_id}/steps/3/lock" in _routes()

    # -- Step 4 routes (questionnaire router) --
    def test_step4_generate_route_exists(self):
        assert "/api/v1/studies/{study_id}/steps/4/generate" in _routes()

    def test_step4_feedback_route_exists(self):
        assert "/api/v1/studies/{study_id}/steps/4/sections/{section_id}/feedback" in _routes()

    def test_step4_lock_route_exists(self):
        assert "/api/v1/studies/{study_id}/steps/4/lock" in _routes()

    # -- Core CRUD --
    def test_health_route_exists(self):
        assert "/health" in _routes()

    def test_create_study_route_exists(self):
        assert "/api/v1/studies" in _routes()


# ────────────────────────────────────────────────────────────
# HTTP Method Tests
# ────────────────────────────────────────────────────────────

class TestHTTPMethods:
    def test_step1_generate_is_post(self):
        rm = _route_methods()
        assert "POST" in rm.get("/api/v1/studies/{study_id}/steps/1/generate", set())

    def test_step1_edit_is_patch(self):
        rm = _route_methods()
        assert "PATCH" in rm.get("/api/v1/studies/{study_id}/steps/1", set())

    def test_step2_generate_is_post(self):
        rm = _route_methods()
        assert "POST" in rm.get("/api/v1/studies/{study_id}/steps/2/generate", set())

    def test_step3_generate_is_post(self):
        rm = _route_methods()
        assert "POST" in rm.get("/api/v1/studies/{study_id}/steps/3/generate", set())

    def test_step4_generate_is_post(self):
        rm = _route_methods()
        assert "POST" in rm.get("/api/v1/studies/{study_id}/steps/4/generate", set())


# ────────────────────────────────────────────────────────────
# State Machine Enforcement Tests
# ────────────────────────────────────────────────────────────

class TestStateMachineEnforcement:
    """Verify the state machine blocks illegal transitions."""

    def test_cannot_skip_from_init_to_step_2(self):
        assert not StudyStateMachine.can_transition("init", "step_2_draft")

    def test_cannot_skip_from_init_to_step_3(self):
        assert not StudyStateMachine.can_transition("init", "step_3_draft")

    def test_cannot_skip_from_init_to_step_4(self):
        assert not StudyStateMachine.can_transition("init", "step_4_draft")

    def test_cannot_skip_from_step_1_locked_to_step_3(self):
        assert not StudyStateMachine.can_transition("step_1_locked", "step_3_draft")

    def test_cannot_skip_from_step_2_locked_to_step_4(self):
        assert not StudyStateMachine.can_transition("step_2_locked", "step_4_draft")

    def test_cannot_lock_without_review(self):
        study = MagicMock()
        study.status = "step_1_draft"
        assert not StudyStateMachine.can_lock_step(study, 1)

    def test_cannot_edit_locked_step(self):
        study = MagicMock()
        study.status = "step_2_locked"
        assert not StudyStateMachine.can_edit_step(study, 2)

    def test_full_lifecycle_transitions_valid(self):
        """Walk through the entire valid lifecycle."""
        statuses = [
            "init", "step_1_draft", "step_1_review", "step_1_locked",
            "step_2_draft", "step_2_review", "step_2_locked",
            "step_3_draft", "step_3_review", "step_3_locked",
            "step_4_draft", "step_4_review", "step_4_locked",
            "complete",
        ]
        for i in range(len(statuses) - 1):
            assert StudyStateMachine.can_transition(statuses[i], statuses[i + 1]), \
                f"Should allow {statuses[i]} -> {statuses[i+1]}"

    def test_complete_is_terminal(self):
        assert StudyStateMachine.TRANSITIONS["complete"] == []

    def test_prerequisites_chain(self):
        assert StudyStateMachine.STEP_PREREQUISITES[1] is None
        assert StudyStateMachine.STEP_PREREQUISITES[2] == "step_1_locked"
        assert StudyStateMachine.STEP_PREREQUISITES[3] == "step_2_locked"
        assert StudyStateMachine.STEP_PREREQUISITES[4] == "step_3_locked"


# ────────────────────────────────────────────────────────────
# Seed Data Tests
# ────────────────────────────────────────────────────────────

class TestSeedData:
    def test_metric_library_json_exists(self):
        import json
        from pathlib import Path
        seed_path = Path(__file__).parent.parent / "seed_data" / "metric_library.json"
        assert seed_path.exists()
        data = json.loads(seed_path.read_text())
        assert isinstance(data, list)

    def test_metric_library_has_expected_count(self):
        import json
        from pathlib import Path
        seed_path = Path(__file__).parent.parent / "seed_data" / "metric_library.json"
        data = json.loads(seed_path.read_text())
        # PRD specifies 18+ metrics
        assert len(data) >= 18

    def test_metric_library_has_purchase_intent(self):
        import json
        from pathlib import Path
        seed_path = Path(__file__).parent.parent / "seed_data" / "metric_library.json"
        data = json.loads(seed_path.read_text())
        ids = [m["id"] for m in data]
        assert "purchase_intent" in ids

    def test_metric_library_has_required_fields(self):
        import json
        from pathlib import Path
        seed_path = Path(__file__).parent.parent / "seed_data" / "metric_library.json"
        data = json.loads(seed_path.read_text())
        required = {"id", "display_name", "category", "applicable_study_types", "default_scale"}
        for metric in data:
            assert required.issubset(set(metric.keys())), f"Missing fields in {metric['id']}"

    def test_all_expected_metric_ids(self):
        import json
        from pathlib import Path
        seed_path = Path(__file__).parent.parent / "seed_data" / "metric_library.json"
        data = json.loads(seed_path.read_text())
        ids = {m["id"] for m in data}
        expected = {
            "purchase_intent", "purchase_frequency", "willingness_to_pay",
            "uniqueness", "differentiation_vs_comp", "overall_appeal",
            "relevance", "believability", "brand_fit", "value_for_money",
            "price_sensitivity", "likes_dislikes", "improvement_suggestions",
            "source_of_volume", "aided_awareness", "brand_consideration",
            "net_promoter_score", "usage_frequency", "brand_last_purchased",
        }
        assert expected.issubset(ids)


# ────────────────────────────────────────────────────────────
# Prompt Template Tests
# ────────────────────────────────────────────────────────────

class TestPromptTemplates:
    def test_study_brief_generator_exists(self):
        from pathlib import Path
        p = Path(__file__).parent.parent / "prompts" / "study_brief_generator.txt"
        assert p.exists()

    def test_concept_refiner_exists(self):
        from pathlib import Path
        p = Path(__file__).parent.parent / "prompts" / "concept_refiner.txt"
        assert p.exists()

    def test_comparability_auditor_exists(self):
        from pathlib import Path
        p = Path(__file__).parent.parent / "prompts" / "comparability_auditor.txt"
        assert p.exists()

    def test_research_design_generator_exists(self):
        from pathlib import Path
        p = Path(__file__).parent.parent / "prompts" / "research_design_generator.txt"
        assert p.exists()

    def test_questionnaire_generator_exists(self):
        from pathlib import Path
        p = Path(__file__).parent.parent / "prompts" / "questionnaire_generator.txt"
        assert p.exists()

    def test_feedback_incorporator_exists(self):
        from pathlib import Path
        p = Path(__file__).parent.parent / "prompts" / "feedback_incorporator.txt"
        assert p.exists()


# ────────────────────────────────────────────────────────────
# Version & Audit Flow Tests
# ────────────────────────────────────────────────────────────

class TestVersionFlow:
    """Test version incrementing logic used across steps."""

    def test_version_starts_at_1(self):
        from app.models.study import StepVersion
        col = StepVersion.__table__.columns["version"]
        assert col.default.arg == 1

    def test_unique_constraint_prevents_duplicate_versions(self):
        from app.models.study import StepVersion
        constraints = [c for c in StepVersion.__table__.constraints
                       if hasattr(c, 'columns') and len(c.columns) > 1]
        col_sets = [{col.name for col in c.columns} for c in constraints]
        assert {"study_id", "step", "version"} in col_sets


class TestAuditFlow:
    """Test audit log model structure."""

    def test_audit_log_action_column_exists(self):
        from app.models.audit import AuditLog
        cols = {c.name for c in AuditLog.__table__.columns}
        assert "action" in cols
        assert "actor" in cols
        assert "payload" in cols

    def test_review_comment_resolved_by_column(self):
        from app.models.audit import ReviewComment
        cols = {c.name for c in ReviewComment.__table__.columns}
        assert "resolved" in cols
        assert "resolved_by" in cols


# ────────────────────────────────────────────────────────────
# Health Check Smoke Test (always works, no DB needed)
# ────────────────────────────────────────────────────────────

class TestSmoke:
    @pytest.mark.asyncio
    async def test_health_returns_200(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_openapi_docs_available(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "paths" in schema
        # Should have many paths from all routers
        assert len(schema["paths"]) >= 15

    @pytest.mark.asyncio
    async def test_openapi_has_tags_for_all_steps(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/openapi.json")
        schema = resp.json()
        tag_names = {t["name"] for t in schema.get("tags", [])} if "tags" in schema else set()
        # Also check paths for tags
        all_tags = set()
        for path_info in schema["paths"].values():
            for method_info in path_info.values():
                for tag in method_info.get("tags", []):
                    all_tags.add(tag)
        assert "Studies" in all_tags
        assert "Concepts" in all_tags
        assert "Research Design" in all_tags
        assert "Questionnaire" in all_tags
        assert "Metrics" in all_tags


# ────────────────────────────────────────────────────────────
# No Coupling Test
# ────────────────────────────────────────────────────────────

class TestNoCoupling:
    """Verify no imports from the existing backend/ directory."""

    def test_no_backend_imports(self):
        import os
        from pathlib import Path

        app_dir = Path(__file__).parent.parent / "app"
        violations = []
        for py_file in app_dir.rglob("*.py"):
            content = py_file.read_text()
            if "from backend" in content or "import backend" in content:
                violations.append(str(py_file))
        assert violations == [], f"Backend imports found in: {violations}"

    def test_no_frontend_imports(self):
        import os
        from pathlib import Path

        app_dir = Path(__file__).parent.parent / "app"
        violations = []
        for py_file in app_dir.rglob("*.py"):
            content = py_file.read_text()
            if "from frontend" in content or "import frontend" in content:
                violations.append(str(py_file))
        assert violations == [], f"Frontend imports found in: {violations}"


# ────────────────────────────────────────────────────────────
# Total Route Count
# ────────────────────────────────────────────────────────────

class TestTotalRoutes:
    def test_minimum_route_count(self):
        """The app should have a healthy number of routes from all routers."""
        routes = [r for r in app.routes if hasattr(r, "methods")]
        # Base: health + 3 study CRUD = 4
        # Step 1: 3, Metrics: 6, Audit: 1, Comments: 3, Versions: 2, Export: 1 = 16
        # Step 2: 7, Step 3: 3, Step 4: 3 = 13
        # Total minimum: ~33
        assert len(routes) >= 25, f"Only found {len(routes)} routes"
