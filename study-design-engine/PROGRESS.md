# Study Design Engine — Progress Tracker

> Last updated: 2026-03-01

## Project Status: Live E2E Verified

The Study Design Engine microservice has been fully implemented, deployed locally, and verified end-to-end with a live LLM (Claude Sonnet 4). All 572 tests pass. Full 4-step lifecycle completed successfully: study creation → brief generation → concept boards → research design → questionnaire → export.

---

## Phase Summary

### Phase 1: Foundation ✅ Complete
**Built by**: Tech Lead
**Tests**: 164

| Component | Status | Files |
|-----------|--------|-------|
| Project structure | ✅ | Full directory tree under `study-design-engine/` |
| Config (Pydantic Settings) | ✅ | `app/config.py` |
| Database (async SQLAlchemy) | ✅ | `app/database.py` |
| Models (6 tables) | ✅ | `app/models/study.py`, `concept.py`, `audit.py`, `metric.py` |
| Schemas (7 modules) | ✅ | `app/schemas/common.py`, `study.py`, `concept.py`, `research_design.py`, `questionnaire.py`, `audit.py`, `metric.py` |
| LLM Client (LiteLLM) | ✅ | `app/llm/client.py` |
| Prompt Service | ✅ | `app/services/prompt_service.py` |
| State Machine | ✅ | `app/services/state_machine.py` |
| Seed Data (19 metrics) | ✅ | `seed_data/metric_library.json` |
| FastAPI main app + CRUD | ✅ | `app/main.py` |
| Dockerfile | ✅ | `Dockerfile` |
| Alembic migrations setup | ✅ | `alembic.ini`, `migrations/env.py` |

### Phase 2: Parallel Implementation ✅ Complete
**Built by**: Engineers A–D (4 parallel streams)
**Tests**: 346

#### Terminal 1 — Step 1 (Study Brief) + Support Services ✅
**Engineer A** | 75 tests

| Service | File | Methods |
|---------|------|---------|
| StudyBriefService | `app/services/study_brief_service.py` | `generate_brief`, `edit_brief`, `lock_brief` |
| MetricLibraryService | `app/services/metric_library_service.py` | `list_metrics`, `get_metric`, `create_metric`, `update_metric`, `delete_metric`, `seed_metrics` |
| AuditService | `app/services/audit_service.py` | `log_event`, `get_study_audit` |
| ReviewCommentService | `app/services/review_comment_service.py` | `add_comment`, `list_comments`, `resolve_comment` |
| VersionHistoryService | `app/services/version_history_service.py` | `get_versions`, `get_version` |
| StudyExportService | `app/services/study_export_service.py` | `export_study` |

**Routers**: `studies.py`, `metrics.py`, `audit.py`, `comments.py`, `versions.py`, `export.py`
**Prompts**: `study_brief_generator.txt`

#### Terminal 2 — Step 2 (Concept Board Builder) ✅
**Engineer B** | 73 tests

| Service | File | Methods |
|---------|------|---------|
| ConceptBoardService | `app/services/concept_board_service.py` | `generate_templates`, `update_concept`, `refine_concept`, `approve_concept`, `comparability_check`, `render_image`, `lock_concepts` |

**Routers**: `concepts.py` (7 endpoints)
**Prompts**: `concept_refiner.txt`, `comparability_auditor.txt`

#### Terminal 3 — Step 3 (Research Design) + Sample Calculator ✅
**Engineer C** | 105 tests

| Service | File | Methods |
|---------|------|---------|
| SampleCalculator | `app/services/sample_calculator.py` | `calculate_sample_size`, `allocate_quotas`, `recalculate_on_edit`, `estimate_field_duration`, `estimate_cost` |
| ResearchDesignService | `app/services/research_design_service.py` | `generate_design`, `edit_design`, `lock_design` |

**Routers**: `research_design.py` (3 endpoints)
**Prompts**: `research_design_generator.txt`

#### Terminal 4 — Step 4 (Questionnaire Builder) ✅
**Engineer D** | 93 tests

| Service | File | Methods |
|---------|------|---------|
| QuestionnaireService | `app/services/questionnaire_service.py` | `generate_questionnaire`, `submit_section_feedback`, `lock_questionnaire`, `estimate_duration`, `validate_questionnaire` |

**Routers**: `questionnaire.py` (3 endpoints)
**Prompts**: `questionnaire_generator.txt`, `feedback_incorporator.txt`

### Phase 3: Integration ✅ Complete
**Built by**: Tech Lead
**Tests**: 62

| Component | Status |
|-----------|--------|
| All 9 routers wired into `main.py` | ✅ |
| Docker Compose (`docker-compose.sde.yml`) | ✅ |
| Integration tests | ✅ 62 tests |
| README updated | ✅ |
| No-coupling verified (zero backend/frontend imports) | ✅ |

---

## Test Suite Breakdown

| Test File | Count | Coverage Area |
|-----------|-------|---------------|
| `test_step4_questionnaire.py` | 93 | Questionnaire schemas, service, duration, validation, prompts, router |
| `test_step2_concepts.py` | 73 | Concept schemas, service (7 methods), prompts, router |
| `test_sample_calculator.py` | 73 | Deterministic calculations, quotas, edge cases, cost/duration |
| `test_integration.py` | 62 | Router wiring, state machine, seed data, prompts, smoke |
| `test_schemas.py` | 43 | All Pydantic schema validation |
| `test_support_services.py` | 40 | Audit, metrics, comments, versions, export services |
| `test_models.py` | 40 | All 6 database models |
| `test_state_machine.py` | 38 | State transitions, prerequisites, locking |
| `test_step1_brief.py` | 35 | Study brief generate, edit, lock |
| `test_step3_research_design.py` | 32 | Research design service, schemas, router |
| `test_config.py` | 17 | Settings fields and defaults |
| `test_llm.py` | 11 | LLM client with mocked litellm |
| `test_prompt_service.py` | 8 | Template loading, formatting, caching |
| `test_health.py` | 7 | Health endpoint, route existence |
| **Total** | **572** | |

---

## API Endpoint Inventory

| # | Method | Path | Step | Router |
|---|--------|------|------|--------|
| 1 | GET | `/health` | — | main.py |
| 2 | POST | `/api/v1/studies` | — | main.py |
| 3 | GET | `/api/v1/studies/{id}` | — | main.py |
| 4 | GET | `/api/v1/studies` | — | main.py |
| 5 | POST | `/api/v1/studies/{id}/steps/1/generate` | 1 | studies.py |
| 6 | PATCH | `/api/v1/studies/{id}/steps/1` | 1 | studies.py |
| 7 | POST | `/api/v1/studies/{id}/steps/1/lock` | 1 | studies.py |
| 8 | POST | `/api/v1/studies/{id}/steps/2/generate` | 2 | concepts.py |
| 9 | PATCH | `/api/v1/studies/{id}/concepts/{cid}` | 2 | concepts.py |
| 10 | POST | `/api/v1/studies/{id}/concepts/{cid}/refine` | 2 | concepts.py |
| 11 | POST | `/api/v1/studies/{id}/concepts/{cid}/approve` | 2 | concepts.py |
| 12 | POST | `/api/v1/studies/{id}/concepts/comparability-check` | 2 | concepts.py |
| 13 | POST | `/api/v1/studies/{id}/concepts/{cid}/render` | 2 | concepts.py |
| 14 | POST | `/api/v1/studies/{id}/steps/2/lock` | 2 | concepts.py |
| 15 | POST | `/api/v1/studies/{id}/steps/3/generate` | 3 | research_design.py |
| 16 | PATCH | `/api/v1/studies/{id}/steps/3` | 3 | research_design.py |
| 17 | POST | `/api/v1/studies/{id}/steps/3/lock` | 3 | research_design.py |
| 18 | POST | `/api/v1/studies/{id}/steps/4/generate` | 4 | questionnaire.py |
| 19 | POST | `/api/v1/studies/{id}/steps/4/sections/{sid}/feedback` | 4 | questionnaire.py |
| 20 | POST | `/api/v1/studies/{id}/steps/4/lock` | 4 | questionnaire.py |
| 21 | GET | `/api/v1/metrics` | — | metrics.py |
| 22 | GET | `/api/v1/metrics/{id}` | — | metrics.py |
| 23 | POST | `/api/v1/metrics` | — | metrics.py |
| 24 | PATCH | `/api/v1/metrics/{id}` | — | metrics.py |
| 25 | DELETE | `/api/v1/metrics/{id}` | — | metrics.py |
| 26 | POST | `/api/v1/metrics/seed` | — | metrics.py |
| 27 | GET | `/api/v1/studies/{id}/audit-log` | — | audit.py |
| 28 | POST | `/api/v1/studies/{id}/comments` | — | comments.py |
| 29 | GET | `/api/v1/studies/{id}/comments` | — | comments.py |
| 30 | POST | `/api/v1/studies/{id}/comments/{cid}/resolve` | — | comments.py |
| 31 | GET | `/api/v1/studies/{id}/steps/{step}/versions` | — | versions.py |
| 32 | GET | `/api/v1/studies/{id}/steps/{step}/versions/{v}` | — | versions.py |
| 33 | GET | `/api/v1/studies/{id}/export` | — | export.py |

---

## File Inventory

### Models (4 files, 6 tables)
- `app/models/study.py` — `studies`, `step_versions`
- `app/models/concept.py` — `concepts`
- `app/models/audit.py` — `review_comments`, `audit_log`
- `app/models/metric.py` — `metric_library`

### Services (12 files)
- `app/services/state_machine.py` — StudyStateMachine (lifecycle enforcement)
- `app/services/prompt_service.py` — Template loading/formatting
- `app/services/study_brief_service.py` — Step 1 generation/edit/lock
- `app/services/concept_board_service.py` — Step 2 concepts pipeline
- `app/services/sample_calculator.py` — Deterministic sample/quota math
- `app/services/research_design_service.py` — Step 3 design generation
- `app/services/questionnaire_service.py` — Step 4 questionnaire pipeline
- `app/services/audit_service.py` — Audit log management
- `app/services/review_comment_service.py` — Review comments CRUD
- `app/services/metric_library_service.py` — Metric library CRUD + seeding
- `app/services/version_history_service.py` — Step version history
- `app/services/study_export_service.py` — Full study export

### Routers (9 files)
- `app/routers/studies.py` — Step 1 endpoints
- `app/routers/concepts.py` — Step 2 endpoints (7 routes)
- `app/routers/research_design.py` — Step 3 endpoints
- `app/routers/questionnaire.py` — Step 4 endpoints
- `app/routers/metrics.py` — Metric library endpoints (6 routes)
- `app/routers/audit.py` — Audit log endpoint
- `app/routers/comments.py` — Review comments endpoints
- `app/routers/versions.py` — Version history endpoints
- `app/routers/export.py` — Study export endpoint

### Prompt Templates (6 files)
- `prompts/study_brief_generator.txt`
- `prompts/concept_refiner.txt`
- `prompts/comparability_auditor.txt`
- `prompts/research_design_generator.txt`
- `prompts/questionnaire_generator.txt`
- `prompts/feedback_incorporator.txt`

---

## Remaining Work / Next Steps

### Immediate (required for live deployment)
- [x] Provision PostgreSQL database (`study_design_engine`) — done, running on localhost:5432
- [x] Run `alembic revision --autogenerate -m "initial_schema"` then `alembic upgrade head` — done, all 6 tables created
- [x] Set `ANTHROPIC_API_KEY` in `.env` — done, using Claude Sonnet 4
- [x] Run `POST /api/v1/metrics/seed` to populate metric library — done, 19 metrics seeded
- [x] End-to-end smoke test with live LLM — **PASSED** (full lifecycle below)

### Live E2E Smoke Test Results (2026-03-01)

| Step | Action | Result |
|------|--------|--------|
| Health | `GET /health` | ✅ healthy |
| Metrics | `POST /metrics/seed` | ✅ 19 metrics |
| Create Study | `POST /studies` (TastyBites snack concepts) | ✅ status=init |
| State Guard | Skip to step 2/3/4 | ✅ All blocked with 400 |
| Step 1 Generate | AI-generated brief | ✅ concept_testing, sequential_monadic, 13 metrics |
| Step 1 Edit | Changed title | ✅ version 2 created |
| Step 1 Lock | Locked with user_id | ✅ step_1_locked |
| Step 2 Generate | 3 concept templates | ✅ raw status |
| Step 2 Update | Filled in 3 concepts (health/family/gourmet) | ✅ |
| Step 2 Refine | AI-refined all 3 | ✅ testability_score=0.85, flags |
| Step 2 Approve | Approved all 3 | ✅ approved status |
| Step 2 Comparability | Cross-concept audit | ✅ "warning" (pricing & language) |
| Step 2 Lock | Locked step 2 | ✅ step_2_locked |
| Step 3 Generate | Research design | ✅ sequential_monadic, 75 respondents |
| Step 3 Edit | Changed MOE 5%→3% | ✅ Reactive recalc: sample 75→209, cost ₹11,250→₹31,350 |
| Step 3 Lock | Locked step 3 | ✅ step_3_locked |
| Step 4 Generate | Full questionnaire | ✅ 8 sections, 31 questions, 12 min, bilingual |
| Step 4 Feedback | Added diet preference Q | ✅ Section updated with change_log |
| Step 4 Lock | Locked + complete | ✅ study status=complete |
| Export | Full study export | ✅ All 4 steps, 7 versions |
| Audit Log | Query audit trail | ✅ 3 entries |
| Comments | Add + list | ✅ |
| Version History | Step 1 versions | ✅ 2 versions |

### Short-term improvements
- [ ] Add Redis caching for prompt templates and metric lookups
- [ ] Add authentication/authorization middleware
- [ ] Add rate limiting for LLM calls
- [ ] Add request/response logging middleware
- [x] Create actual Alembic migration files — done (migrations/versions/71b3ceacd3e0_initial_schema.py)

### Medium-term enhancements
- [ ] Implement real image rendering (Puppeteer HTML-to-image) for concept boards
- [ ] Add WebSocket support for real-time step progress updates
- [ ] Add batch study creation endpoint
- [ ] Implement study cloning/templating
- [ ] Add benchmark data integration for metrics

### Bugs Fixed During Live Testing
- `study_brief_service.py`: `uuid.UUID(user_id)` crash when user_id is not a UUID — added try/except
- `research_design_service.py`: `generate_design` only transitioned to `step_3_draft`, never to `step_3_review` — added second transition
- `research_design_service.py`: Same UUID parsing bug in `lock_design` — added try/except
- `questionnaire_service.py`: Same UUID parsing bug in `lock_questionnaire` — added try/except
- `concept_board_service.py`: Same UUID parsing bug in `lock_concepts` — added `_safe_uuid` helper
- `llm/client.py`: max_tokens=4096 too small for questionnaire generation — increased to 16000
- `llm/client.py`: Improved JSON extraction with brace-matching and trailing comma removal
- `schemas/questionnaire.py`: `QuestionScale.options` was required but LLM returns `anchors` dict — made `options` optional with `anchors` alternative

### Known Limitations
- Image rendering is placeholder only (stores URL pattern, no actual rendering)
- No authentication — all endpoints are open
- No Redis integration yet (configured but not used)
- LLM calls require external API keys to function
- Steps 2-4 services don't call AuditService (only Step 1 has full audit logging)
- 307 redirects on some endpoints without trailing slash (FastAPI default behavior)

---

## Architecture Decisions

1. **Standalone microservice**: No coupling to existing `backend/` or `frontend/` — verified by automated test
2. **Port 8001**: Avoids conflict with existing backend on 8000
3. **State machine**: All status transitions enforced centrally — prevents invalid step sequencing
4. **Deterministic calculator**: Sample size/quota math is pure Python (no LLM) — testable and predictable
5. **LLM recommends, calculator computes**: LLM suggests methodology; `SampleCalculator` does the math
6. **Version history**: Every edit creates a new version — full audit trail with no data loss
7. **Section-by-section feedback**: Questionnaire edits target specific sections, not the whole document
