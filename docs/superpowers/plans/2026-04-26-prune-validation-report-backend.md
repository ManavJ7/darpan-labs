# Prune Orphan Validation-Report Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the validation-report REST endpoints, Pydantic schemas, SQLAlchemy model, `validation_reports` table, and Celery task — all orphaned after the SDE frontend stopped consuming them.

**Architecture:** Pure deletion across two services (`study-design-engine/`, `ai-interviewer/backend/`) plus two Alembic migrations that drop the table with `IF EXISTS` on the upgrade and recreate the original column shape on the downgrade. No tests are added — verification is a Python import smoke check on each backend. Four commits, each scoped to one logical removal.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2 with async, Alembic, Celery, PostgreSQL.

Spec: [docs/superpowers/specs/2026-04-26-prune-validation-report-backend-design.md](../specs/2026-04-26-prune-validation-report-backend-design.md)

---

## File Structure

**Modified:**
- `study-design-engine/app/routers/simulation.py` — delete the validation-report block (~169 lines from lines 636–808 inclusive)
- `study-design-engine/app/models/twin.py` — delete `ValidationReport` class (lines 75–91)
- `study-design-engine/app/models/__init__.py` — drop `ValidationReport` from import + `__all__`
- `ai-interviewer/backend/app/models/twin.py` — delete `ValidationReport` class (lines 297–328)
- `ai-interviewer/backend/app/models/__init__.py` — drop `ValidationReport` from import + `__all__`
- `ai-interviewer/backend/app/tasks/twin_tasks.py` — drop the import on line 21, the module docstring mention on line 1, and the `run_validation_report` task block (lines 400–606)

**Created:**
- `study-design-engine/migrations/versions/f6a7b8c9d0e1_drop_validation_reports.py` — drop the table; downgrade recreates the original schema
- `ai-interviewer/backend/migrations/versions/003_drop_validation_reports.py` — same body, different revision id, parents `002_twin_pipeline`

**Out of scope — do NOT touch:**
- `pipeline_jobs` table or any other shared table
- `validation-dashboard/scripts/` (the static dashboard's analysis pipeline lives separately and stays)
- `study-design-engine/app/celery_app.py` (the Celery client that dispatches `twin.run_validation_report` from the now-deleted endpoint goes when the endpoint goes — no separate cleanup needed)

**Branch:** direct commits to `main`, matching prior session policy.

**Working tree state at plan time:** Clean. (Earlier sessions left some unrelated changes; the user has since committed all of them.)

---

## Task 1: Remove validation-report endpoints and schemas from SDE router

**Files:**
- Modify: `study-design-engine/app/routers/simulation.py`

The endpoints, schemas, and the import-level reference to `ValidationReport` all live in this single file. Removing them now (before deleting the model) is safe because no other file in the SDE backend imports these symbols.

- [ ] **Step 1: Drop `ValidationReport` from the imports**

In `study-design-engine/app/routers/simulation.py`, locate the import on line 21:

```python
from app.models.twin import DigitalTwin, Participant, PipelineJob, TwinSimulationRun, ValidationReport
```

Use Edit with `replace_all: false`. `old_string` = the line above; `new_string`:

```python
from app.models.twin import DigitalTwin, Participant, PipelineJob, TwinSimulationRun
```

- [ ] **Step 2: Delete the entire validation-report section (banner comment + 3 schemas + 3 endpoints)**

This is a single contiguous block from line 636 through line 808 inclusive (~173 lines counting trailing blank). Use Edit. `old_string`:

```python
# ===========================================================================
# Validation Report endpoints
# ===========================================================================

class ValidationReportRequest(BaseModel):
    mode: str = "synthesis"  # "comparison" (real vs twin) or "synthesis" (twin-only)


class ValidationReportResponse(BaseModel):
    report_id: str
    job_id: str
    mode: str
    status: str
    status_url: str


class ValidationReportDetail(BaseModel):
    report_id: str
    study_id: str
    mode: str
    status: str
    twin_count: int | None
    real_count: int | None
    report_data: dict | None
    created_at: str
    completed_at: str | None


@router.post(
    "/validation-report",
    response_model=ValidationReportResponse,
    status_code=202,
)
async def create_validation_report(
    study_id: uuid.UUID,
    request: ValidationReportRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate a validation report from twin simulation results.

    Modes:
    - "synthesis": Analyze twin responses only (aggregate stats, T2B, composites, etc.)
    - "comparison": Compare twin responses against real participant M8 interview data
    """
    study = await require_study_owner(study_id, current_user, db)

    # Check that completed simulations exist
    sim_result = await db.execute(
        select(TwinSimulationRun).where(
            and_(
                TwinSimulationRun.study_id == study_id,
                TwinSimulationRun.status == "completed",
            )
        )
    )
    completed_sims = sim_result.scalars().all()
    if not completed_sims:
        raise HTTPException(
            status_code=400,
            detail="No completed twin simulations found. Run simulations first.",
        )

    # Check for existing pending/running report
    existing_result = await db.execute(
        select(ValidationReport).where(
            and_(
                ValidationReport.study_id == study_id,
                ValidationReport.mode == request.mode,
                ValidationReport.status.in_(["pending", "running"]),
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Validation report already in progress (report {existing.id})",
        )

    # Create job and report
    job = PipelineJob(
        job_type="run_validation",
        study_id=study_id,
        config={"mode": request.mode},
    )
    db.add(job)
    await db.flush()

    report = ValidationReport(
        study_id=study_id,
        job_id=job.id,
        mode=request.mode,
    )
    db.add(report)
    await db.flush()
    await db.commit()

    # Dispatch Celery task
    from app.celery_app import celery_app as celery
    celery.send_task(
        "twin.run_validation_report",
        args=[str(job.id), str(report.id)],
    )

    return ValidationReportResponse(
        report_id=str(report.id),
        job_id=str(job.id),
        mode=request.mode,
        status="pending",
        status_url=f"/api/v1/studies/{study_id}/validation-report/{report.id}",
    )


@router.get("/validation-report/{report_id}", response_model=ValidationReportDetail)
async def get_validation_report(
    study_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """Get a validation report by ID."""
    result = await db.execute(
        select(ValidationReport).where(
            and_(
                ValidationReport.id == report_id,
                ValidationReport.study_id == study_id,
            )
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Validation report not found")

    return ValidationReportDetail(
        report_id=str(report.id),
        study_id=str(report.study_id),
        mode=report.mode,
        status=report.status,
        twin_count=report.twin_count,
        real_count=report.real_count,
        report_data=report.report_data,
        created_at=report.created_at.isoformat(),
        completed_at=report.completed_at.isoformat() if report.completed_at else None,
    )


@router.get("/validation-reports", response_model=list[ValidationReportDetail])
async def list_validation_reports(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """List all validation reports for a study."""
    result = await db.execute(
        select(ValidationReport)
        .where(ValidationReport.study_id == study_id)
        .order_by(ValidationReport.created_at.desc())
    )
    reports = result.scalars().all()

    return [
        ValidationReportDetail(
            report_id=str(r.id),
            study_id=str(r.study_id),
            mode=r.mode,
            status=r.status,
            twin_count=r.twin_count,
            real_count=r.real_count,
            report_data=r.report_data,
            created_at=r.created_at.isoformat(),
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
        )
        for r in reports
    ]
```

`new_string` is empty.

- [ ] **Step 3: Verify the router compiles**

Run from repo root:

```bash
cd study-design-engine && python -c "from app.routers import simulation; print('ok')" && cd ..
```

Expected: prints `ok`. If it fails with `ImportError: cannot import name 'ValidationReport'`, that means the model deletion in Task 2 has already happened in this working tree — recover by continuing to Task 2; otherwise fix whatever the error indicates.

If the local Python environment cannot resolve dependencies (`fastapi`, `sqlalchemy`, etc.) because no virtualenv is active, document the environment failure in the report but DO NOT install anything globally. The Railway container has its own environment; the smoke check is a local convenience, not a gate.

- [ ] **Step 4: Confirm zero remaining references in the SDE backend**

Run:

```bash
grep -rn "ValidationReport\|validation_reports\|validation-report" study-design-engine/app/ 2>/dev/null
```

Expected: zero matches.

- [ ] **Step 5: Commit**

```bash
git add study-design-engine/app/routers/simulation.py
git commit -m "sde-api: remove validation-report endpoints and schemas"
```

Confirm only the one file is in the commit: `git show --stat HEAD | head -3`.

---

## Task 2: Remove the SDE `ValidationReport` model and add the drop-table migration

**Files:**
- Modify: `study-design-engine/app/models/twin.py`
- Modify: `study-design-engine/app/models/__init__.py`
- Create: `study-design-engine/migrations/versions/f6a7b8c9d0e1_drop_validation_reports.py`

The migration is created in this task (not a separate one) so a `git bisect` landing on this commit always sees the model and the schema-drop in lockstep.

- [ ] **Step 1: Delete the `ValidationReport` class from the model file**

In `study-design-engine/app/models/twin.py`, use Edit. `old_string`:

```python
class ValidationReport(Base):
    """Validation report comparing twin simulation results (optionally vs real responses)."""

    __tablename__ = "validation_reports"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("studies.id"), nullable=False, index=True)
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("pipeline_jobs.id", ondelete="SET NULL"), nullable=True,
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)  # comparison, synthesis
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    twin_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    real_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    report_data: Mapped[Optional[dict]] = mapped_column(pg.JSONB, nullable=True)  # full validation output
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


```

`new_string` is empty. (The `\n\n` trailing blank line is included so the next class — `TwinSimulationRun` — sits cleanly two lines below `PipelineJob`.)

- [ ] **Step 2: Update `__init__.py` to drop the import and `__all__` entry**

In `study-design-engine/app/models/__init__.py`, use Edit. `old_string`:

```python
from app.models.twin import Participant, DigitalTwin, PipelineJob, TwinSimulationRun, ValidationReport
```

`new_string`:

```python
from app.models.twin import Participant, DigitalTwin, PipelineJob, TwinSimulationRun
```

Then a second Edit. `old_string`:

```python
    "TwinSimulationRun",
    "ValidationReport",
]
```

`new_string`:

```python
    "TwinSimulationRun",
]
```

- [ ] **Step 3: Create the SDE drop-table migration**

Write the new file `study-design-engine/migrations/versions/f6a7b8c9d0e1_drop_validation_reports.py` with this content:

```python
"""drop validation_reports table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-26 00:00:00.000000

The validation_reports table backed an unused REST surface. The frontend
stopped calling those endpoints (commits 0f79481, 8e286f6, e0c1dc6 on main),
the backend endpoints/model/Celery task were removed, and no consumer
remains. Drop the table.

Idempotent on upgrade (`IF EXISTS`) — works whether the SDE chain or the
ai-interviewer chain created the table first. Downgrade recreates the
original column shape so a future revival has a working schema.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS validation_reports CASCADE")


def downgrade() -> None:
    op.create_table(
        'validation_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('study_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('pipeline_jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('mode', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('twin_count', sa.Integer(), nullable=True),
        sa.Column('real_count', sa.Integer(), nullable=True),
        sa.Column('report_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
```

- [ ] **Step 4: Verify SDE backend imports clean**

Run:

```bash
cd study-design-engine && python -c "from app.models import *; from app.routers import simulation; print('ok')" && cd ..
```

Expected: `ok`. Same caveat as Task 1 step 3 — if no Python env is set up, document and continue.

- [ ] **Step 5: Confirm zero remaining references in the SDE backend**

Run:

```bash
grep -rn "ValidationReport" study-design-engine/app/ 2>/dev/null
```

Expected: zero matches. (`validation_reports` may still appear in the new migration file; that's fine — grep for the model class name only.)

- [ ] **Step 6: Commit**

```bash
git add study-design-engine/app/models/twin.py study-design-engine/app/models/__init__.py study-design-engine/migrations/versions/f6a7b8c9d0e1_drop_validation_reports.py
git commit -m "sde-api: remove ValidationReport model + drop table migration"
```

Confirm exactly 3 files: `git show --stat HEAD | head -6`.

---

## Task 3: Remove the ai-interviewer `ValidationReport` model and add the drop-table migration

**Files:**
- Modify: `ai-interviewer/backend/app/models/twin.py`
- Modify: `ai-interviewer/backend/app/models/__init__.py`
- Create: `ai-interviewer/backend/migrations/versions/003_drop_validation_reports.py`

- [ ] **Step 1: Delete the `ValidationReport` class from the ai-interviewer model**

In `ai-interviewer/backend/app/models/twin.py`, use Edit. `old_string`:

```python
class ValidationReport(Base):
    """Validation report comparing twin simulation results (optionally vs real responses)."""

    __tablename__ = "validation_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)  # comparison, synthesis
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending",
    )
    twin_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    real_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    def __repr__(self) -> str:
        return f"<ValidationReport(id={self.id}, mode={self.mode}, status={self.status})>"
```

`new_string` is empty.

- [ ] **Step 2: Update `__init__.py` to drop the import and `__all__` entry**

In `ai-interviewer/backend/app/models/__init__.py`, use Edit. `old_string`:

```python
from .twin import Participant, DigitalTwin, PipelineJob, PipelineStepOutput, ValidationReport, SimulationRun
```

`new_string`:

```python
from .twin import Participant, DigitalTwin, PipelineJob, PipelineStepOutput, SimulationRun
```

Second Edit. `old_string`:

```python
    "ValidationReport",
```

`new_string` is empty.

- [ ] **Step 3: Create the ai-interviewer drop-table migration**

Write `ai-interviewer/backend/migrations/versions/003_drop_validation_reports.py` with this content:

```python
"""drop validation_reports table

Revision ID: 003_drop_validation_reports
Revises: 002_twin_pipeline
Create Date: 2026-04-26 00:00:00.000000

Mirror of the SDE drop migration. The validation_reports table was created
by 002_add_twin_pipeline_tables but is no longer used. Drop it idempotently
(IF EXISTS handles the case where the SDE chain already dropped it on the
shared DB). Downgrade recreates the original column shape.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '003_drop_validation_reports'
down_revision: Union[str, None] = '002_twin_pipeline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS validation_reports CASCADE")


def downgrade() -> None:
    op.create_table(
        'validation_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('study_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('pipeline_jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('mode', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('twin_count', sa.Integer(), nullable=True),
        sa.Column('real_count', sa.Integer(), nullable=True),
        sa.Column('report_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
```

- [ ] **Step 4: Confirm zero remaining references to the model class in `ai-interviewer/backend/app/models`**

Run:

```bash
grep -rn "ValidationReport" ai-interviewer/backend/app/models/ 2>/dev/null
```

Expected: zero matches.

(Note: Task 4 will clean up the `ValidationReport` references in `ai-interviewer/backend/app/tasks/twin_tasks.py`. They will still appear in this grep until then if you broaden the path.)

- [ ] **Step 5: Commit**

```bash
git add ai-interviewer/backend/app/models/twin.py ai-interviewer/backend/app/models/__init__.py ai-interviewer/backend/migrations/versions/003_drop_validation_reports.py
git commit -m "ai-interviewer: remove ValidationReport model + drop table migration"
```

---

## Task 4: Remove the `run_validation_report` Celery task

**Files:**
- Modify: `ai-interviewer/backend/app/tasks/twin_tasks.py`

The Celery task is the last piece. It imports `ValidationReport` (already removed from `app.models` in Task 3, so the file is currently broken — fix it here) and dispatches the validation pipeline.

- [ ] **Step 1: Fix the module docstring**

`ai-interviewer/backend/app/tasks/twin_tasks.py` line 1 currently reads:

```python
"""Celery tasks for twin pipeline: create_twin_pipeline, run_simulation_pipeline, run_validation_report."""
```

Use Edit. `old_string` = the line above; `new_string`:

```python
"""Celery tasks for twin pipeline: create_twin_pipeline, run_simulation_pipeline."""
```

- [ ] **Step 2: Drop `ValidationReport` from the imports**

Find the model import block near the top of `twin_tasks.py` (the explore showed it at line 21 inside a multi-import statement). Read lines 15–30 of the file to see the exact shape, then use Edit.

If the import block currently looks like:

```python
from app.models import (
    PipelineJob,
    Participant,
    DigitalTwin,
    PipelineStepOutput,
    ValidationReport,
    SimulationRun,
)
```

`old_string` = that block; `new_string` = the same block with the `    ValidationReport,` line removed. **Read first to confirm the exact block shape — if it's a single-line import, use a single-line replacement instead.** Do NOT guess the format.

- [ ] **Step 3: Delete the entire `run_validation_report` task block**

The task spans the section banner through the final `raise` at line 606. Use Edit. `old_string`:

```python
# ---------------------------------------------------------------------------
# Task 3: Run Validation Report
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="twin.run_validation_report")
def run_validation_report(self, job_id: str, report_id: str):
```

This won't be unique enough if there's other text matching — instead, use Read to capture lines 400–610 of `ai-interviewer/backend/app/tasks/twin_tasks.py` exactly, and use the full ~210-line block as `old_string`. The block starts at the `# Task 3: Run Validation Report` banner (around line 401) and ends at the `raise` on line 605. Include the trailing blank line on line 606 if present.

`new_string` is empty.

- [ ] **Step 4: Verify ai-interviewer backend imports clean**

Run:

```bash
cd ai-interviewer/backend && python -c "from app.models import *; from app.tasks import twin_tasks; print('ok')" && cd ../..
```

Expected: `ok`. Same env caveat as before.

- [ ] **Step 5: Confirm zero remaining references**

Run from repo root:

```bash
grep -rn "ValidationReport\|run_validation_report" ai-interviewer/backend/app/ 2>/dev/null
grep -rn "twin\.run_validation_report" . --include="*.py" 2>/dev/null
```

Expected: zero matches in both.

- [ ] **Step 6: Commit**

```bash
git add ai-interviewer/backend/app/tasks/twin_tasks.py
git commit -m "ai-interviewer: remove run_validation_report Celery task"
```

---

## Task 5: Final verification

No commit. Just sanity checks before the work is declared done.

- [ ] **Step 1: Whole-monorepo grep**

```bash
grep -rn "ValidationReport\|run_validation_report\|validation_reports" \
  study-design-engine/app/ \
  ai-interviewer/backend/app/ \
  ai-interviewer/backend/migrations/ \
  study-design-engine/migrations/ \
  2>/dev/null
```

Expected matches: ONLY in the two new migration files (which legitimately reference `validation_reports` for the `DROP TABLE` and `create_table` calls). No matches in `app/` for either service.

If anything else surfaces, a deletion was missed — diagnose, fix in the relevant Task's commit, and re-run.

- [ ] **Step 2: Confirm the four expected commits**

```bash
git log --oneline -6
```

Expected, top-to-bottom (most recent first):

1. `ai-interviewer: remove run_validation_report Celery task`
2. `ai-interviewer: remove ValidationReport model + drop table migration`
3. `sde-api: remove ValidationReport model + drop table migration`
4. `sde-api: remove validation-report endpoints and schemas`
5. `docs: implementation plan for orphan validation-report backend cleanup` (this plan)
6. `docs: design spec for orphan validation-report backend cleanup`

If any commit is missing or out of order, the implementer flagged a problem mid-task — investigate before declaring complete.

- [ ] **Step 3: Footprint sanity-check**

```bash
git diff --stat 5ef5d1d..HEAD -- study-design-engine/app/ ai-interviewer/backend/app/ study-design-engine/migrations/ ai-interviewer/backend/migrations/
```

Expected: well over 400 deletions (the two model classes + one router block + one Celery task) and ~70 insertions (two new migration files).

- [ ] **Step 4: Hand back**

Report to the controller:
- Final 4 commit SHAs
- Total `git diff --stat` output for the four touched directories
- Anything skipped or that needs follow-up (e.g., if local Python env was missing and the import smoke checks could not run — Railway will catch any regressions on first deploy because `alembic upgrade head` and `python -c "from app.main import app"` happen during container startup)
