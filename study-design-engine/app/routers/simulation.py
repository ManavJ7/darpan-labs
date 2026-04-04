"""
Simulation endpoints: serve questionnaire payload for twin simulation,
store and retrieve simulation results, manage twin-based simulations.
"""
import csv
import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_session
from app.models.study import Study, StepVersion
from app.models.twin import DigitalTwin, Participant, PipelineJob, TwinSimulationRun, ValidationReport
from app.schemas.simulation import (
    SimulationPayload,
    SimulationQuestion,
    ConceptText,
    SimulationResultUpload,
    SimulationRunResponse,
)

router = APIRouter(
    prefix=f"{settings.API_V1_PREFIX}/studies/{{study_id}}",
    tags=["simulation"],
)


def _extract_concept_text(components: dict, concept_index: int) -> ConceptText:
    """Extract display text from concept components, handling raw/refined/approved formats."""
    def _get(field: str) -> str:
        comp = components.get(field, {})
        if isinstance(comp, dict):
            # Prefer approved brand_edit > refined > raw_input
            return comp.get("brand_edit") or comp.get("refined") or comp.get("raw_input") or ""
        return str(comp)

    return ConceptText(
        concept_index=concept_index,
        product_name=_get("product_name"),
        consumer_insight=_get("consumer_insight"),
        key_benefit=_get("key_benefit"),
        reasons_to_believe=_get("reasons_to_believe"),
    )


@router.get("/simulation-payload", response_model=SimulationPayload)
async def get_simulation_payload(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """Serve a clean questionnaire + concept text payload for twin simulation."""
    # Load study
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    if study.status not in ("step_4_locked", "complete"):
        raise HTTPException(
            status_code=400,
            detail=f"Study must be locked or complete to simulate. Current status: {study.status}",
        )

    # Get locked questionnaire (step 4, latest version with status=locked)
    q_result = await db.execute(
        select(StepVersion)
        .where(StepVersion.study_id == study_id, StepVersion.step == 4, StepVersion.status == "locked")
        .order_by(StepVersion.version.desc())
        .limit(1)
    )
    q_version = q_result.scalar_one_or_none()
    if not q_version:
        raise HTTPException(status_code=400, detail="No locked questionnaire found")

    content = q_version.content

    # Extract questions from sections
    questions: list[SimulationQuestion] = []
    for section in content.get("sections", []):
        for q in section.get("questions", []):
            questions.append(SimulationQuestion(
                question_id=q["question_id"],
                question_text=q.get("question_text", {}),
                question_type=q.get("question_type", "open_text"),
                scale=q.get("scale"),
                show_if=q.get("show_if"),
                required=q.get("required", True),
                section=section.get("section_id", ""),
                position_in_section=q.get("position_in_section", 0),
            ))

    # Get locked concept boards (step 2)
    concepts: list[ConceptText] = []
    c_result = await db.execute(
        select(StepVersion)
        .where(StepVersion.study_id == study_id, StepVersion.step == 2, StepVersion.status == "locked")
        .order_by(StepVersion.version.desc())
        .limit(1)
    )
    c_version = c_result.scalar_one_or_none()
    if c_version and c_version.content:
        for c in c_version.content.get("concepts", []):
            comp = c.get("components", {})
            idx = c.get("concept_index", 0)
            concepts.append(_extract_concept_text(comp, idx))

    return SimulationPayload(
        study_id=str(study_id),
        study_title=study.title,
        brand_name=study.brand_name,
        category=study.category,
        questions=questions,
        concepts=concepts,
    )


@router.post("/simulation-results", response_model=SimulationRunResponse)
async def upload_simulation_results(
    study_id: uuid.UUID,
    data: SimulationResultUpload,
    db: AsyncSession = Depends(get_session),
):
    """Upload simulation results from the bridge script."""
    # Verify study exists
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    run = SimulationRun(
        study_id=study_id,
        status="completed",
        inference_mode=data.inference_mode,
        twin_count=data.twin_count,
        question_count=data.question_count,
        results=data.model_dump(),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    return SimulationRunResponse(
        id=run.id,
        study_id=run.study_id,
        status=run.status,
        inference_mode=run.inference_mode,
        twin_count=run.twin_count,
        question_count=run.question_count,
        results=run.results,
        summary=run.summary,
        created_at=run.created_at,
    )


@router.get("/simulation-results", response_model=list[SimulationRunResponse])
async def list_simulation_results(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """List all simulation runs for a study."""
    result = await db.execute(
        select(SimulationRun)
        .where(SimulationRun.study_id == study_id)
        .order_by(SimulationRun.created_at.desc())
    )
    runs = result.scalars().all()
    return [
        SimulationRunResponse(
            id=r.id,
            study_id=r.study_id,
            status=r.status,
            inference_mode=r.inference_mode,
            twin_count=r.twin_count,
            question_count=r.question_count,
            results=r.results,
            summary=r.summary,
            created_at=r.created_at,
        )
        for r in runs
    ]


@router.get("/simulation-results/{run_id}/export")
async def export_simulation_results(
    study_id: uuid.UUID,
    run_id: uuid.UUID,
    format: str = "json",
    db: AsyncSession = Depends(get_session),
):
    """Export simulation results as JSON or CSV."""
    result = await db.execute(
        select(SimulationRun).where(
            SimulationRun.id == run_id,
            SimulationRun.study_id == study_id,
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Simulation run not found")

    data = run.results

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)

        # Build header from first twin's responses
        twin_results = data.get("results", [])
        if not twin_results:
            raise HTTPException(status_code=400, detail="No results to export")

        # Collect all question IDs in order
        q_ids = []
        for resp in twin_results[0].get("responses", []):
            q_ids.append(resp["question_id"])

        header = ["twin_id", "participant_id", "coherence_score"]
        for qid in q_ids:
            header.extend([qid, f"{qid}_raw"])
        writer.writerow(header)

        for twin in twin_results:
            row = [
                twin.get("twin_id", ""),
                twin.get("participant_id", ""),
                twin.get("coherence_score", ""),
            ]
            resp_map = {r["question_id"]: r for r in twin.get("responses", [])}
            for qid in q_ids:
                r = resp_map.get(qid, {})
                row.append(r.get("structured_answer", ""))
                row.append(r.get("raw_answer", ""))
            writer.writerow(row)

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=simulation_{run_id}.csv"},
        )

    # Default: JSON
    return data


# ===========================================================================
# Twin-based simulation endpoints
# ===========================================================================

class AvailableTwinResponse(BaseModel):
    twin_id: str
    twin_external_id: str
    participant_external_id: str
    participant_name: str | None
    mode: str
    coherence_score: float | None
    status: str


class SimulateTwinsRequest(BaseModel):
    twin_ids: list[str]  # UUIDs as strings
    inference_mode: str = "combined"


class SimulationJobItem(BaseModel):
    job_id: str
    twin_id: str
    twin_external_id: str
    simulation_id: str
    status: str  # pending, already_completed, already_running


class SimulateTwinsResponse(BaseModel):
    jobs: list[SimulationJobItem]


class TwinSimulationResultResponse(BaseModel):
    simulation_id: str
    twin_id: str
    twin_external_id: str
    inference_mode: str
    status: str
    responses: list | None
    summary_stats: dict | None
    created_at: str
    completed_at: str | None


@router.get("/available-twins", response_model=list[AvailableTwinResponse])
async def get_available_twins(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """List all digital twins available for simulation (status='ready')."""
    # Verify study exists and is ready for simulation
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    if study.status not in ("step_4_locked", "complete"):
        raise HTTPException(
            status_code=400,
            detail=f"Study must be locked or complete. Current status: {study.status}",
        )

    # Get all ready twins with participant info
    twin_result = await db.execute(
        select(DigitalTwin)
        .where(DigitalTwin.status == "ready")
        .options(selectinload(DigitalTwin.participant))
        .order_by(DigitalTwin.twin_external_id)
    )
    twins = twin_result.scalars().all()

    return [
        AvailableTwinResponse(
            twin_id=str(t.id),
            twin_external_id=t.twin_external_id,
            participant_external_id=t.participant.external_id,
            participant_name=t.participant.display_name,
            mode=t.mode,
            coherence_score=t.coherence_score,
            status=t.status,
        )
        for t in twins
    ]


@router.post(
    "/simulate",
    response_model=SimulateTwinsResponse,
    status_code=202,
)
async def simulate_twins(
    study_id: uuid.UUID,
    request: SimulateTwinsRequest,
    db: AsyncSession = Depends(get_session),
):
    """Trigger simulation for selected twins using the study's locked questionnaire."""
    # Verify study and get locked questionnaire
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    if study.status not in ("step_4_locked", "complete"):
        raise HTTPException(status_code=400, detail="Study must be locked or complete")

    # Get locked questionnaire
    q_result = await db.execute(
        select(StepVersion)
        .where(StepVersion.study_id == study_id, StepVersion.step == 4, StepVersion.status == "locked")
        .order_by(StepVersion.version.desc())
        .limit(1)
    )
    q_version = q_result.scalar_one_or_none()
    if not q_version:
        raise HTTPException(status_code=400, detail="No locked questionnaire found")

    # Extract questions in flat format for the twin-generator
    content = q_version.content
    questions = []
    for section in content.get("sections", []):
        for q in section.get("questions", []):
            q_text = q.get("question_text", {})
            questions.append({
                "question_id": q["question_id"],
                "question_text": q_text.get("en", str(q_text)) if isinstance(q_text, dict) else str(q_text),
                "question_type": q.get("question_type", "open_text"),
                "section": section.get("section_id", ""),
                "scale": q.get("scale"),
                "options": q.get("options"),
                "matrix_items": q.get("matrix_items"),
                "show_if": q.get("show_if"),
                "required": q.get("required", True),
                "position_in_section": q.get("position_in_section", 0),
            })

    # Get concepts
    concepts = []
    c_result = await db.execute(
        select(StepVersion)
        .where(StepVersion.study_id == study_id, StepVersion.step == 2, StepVersion.status == "locked")
        .order_by(StepVersion.version.desc())
        .limit(1)
    )
    c_version = c_result.scalar_one_or_none()
    if c_version and c_version.content:
        for c in c_version.content.get("concepts", []):
            comp = c.get("components", {})
            ct = _extract_concept_text(comp, c.get("concept_index", 0))
            concepts.append(ct.model_dump())

    questionnaire_snapshot = {"questions": questions, "concepts": concepts}

    # Process each twin
    jobs = []
    for twin_id_str in request.twin_ids:
        twin_uuid = uuid.UUID(twin_id_str)
        twin = await db.get(DigitalTwin, twin_uuid)
        if not twin:
            raise HTTPException(status_code=404, detail=f"Twin {twin_id_str} not found")
        if twin.status != "ready":
            raise HTTPException(status_code=400, detail=f"Twin {twin.twin_external_id} is not ready (status: {twin.status})")

        # Check for existing completed simulation for same twin + study
        existing_sim = await db.execute(
            select(TwinSimulationRun).where(
                and_(
                    TwinSimulationRun.twin_id == twin_uuid,
                    TwinSimulationRun.study_id == study_id,
                    TwinSimulationRun.status == "completed",
                )
            ).order_by(TwinSimulationRun.created_at.desc()).limit(1)
        )
        existing = existing_sim.scalar_one_or_none()
        if existing:
            jobs.append(SimulationJobItem(
                job_id="existing",
                twin_id=str(twin.id),
                twin_external_id=twin.twin_external_id,
                simulation_id=str(existing.id),
                status="already_completed",
            ))
            continue

        # Check for in-progress job
        active_result = await db.execute(
            select(PipelineJob).where(
                and_(
                    PipelineJob.job_type == "run_simulation",
                    PipelineJob.study_id == study_id,
                    PipelineJob.status.in_(["pending", "running"]),
                )
            )
        )
        active_jobs = active_result.scalars().all()
        found_active = False
        for aj in active_jobs:
            sim_check = await db.execute(
                select(TwinSimulationRun).where(
                    and_(TwinSimulationRun.job_id == aj.id, TwinSimulationRun.twin_id == twin_uuid)
                )
            )
            if sim_check.scalar_one_or_none():
                jobs.append(SimulationJobItem(
                    job_id=str(aj.id),
                    twin_id=str(twin.id),
                    twin_external_id=twin.twin_external_id,
                    simulation_id="in_progress",
                    status="already_running",
                ))
                found_active = True
                break
        if found_active:
            continue

        # Create job and simulation run
        job = PipelineJob(
            job_type="run_simulation",
            study_id=study_id,
            config={"inference_mode": request.inference_mode},
        )
        db.add(job)
        await db.flush()

        sim_run = TwinSimulationRun(
            job_id=job.id,
            twin_id=twin_uuid,
            study_id=study_id,
            questionnaire_snapshot=questionnaire_snapshot,
            inference_mode=request.inference_mode,
        )
        db.add(sim_run)
        await db.flush()

        jobs.append(SimulationJobItem(
            job_id=str(job.id),
            twin_id=str(twin.id),
            twin_external_id=twin.twin_external_id,
            simulation_id=str(sim_run.id),
            status="pending",
        ))

    await db.commit()

    # Dispatch Celery tasks for pending jobs
    from app.celery_app import celery_app as celery
    for item in jobs:
        if item.status == "pending":
            celery.send_task(
                "twin.run_simulation",
                args=[item.job_id, item.simulation_id],
            )

    return SimulateTwinsResponse(jobs=jobs)


@router.get("/twin-simulation-results", response_model=list[TwinSimulationResultResponse])
async def list_twin_simulation_results(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """List all twin simulation results for a study."""
    result = await db.execute(
        select(TwinSimulationRun)
        .where(TwinSimulationRun.study_id == study_id)
        .options(selectinload(TwinSimulationRun.twin))
        .order_by(TwinSimulationRun.created_at.desc())
    )
    runs = result.scalars().all()

    return [
        TwinSimulationResultResponse(
            simulation_id=str(r.id),
            twin_id=str(r.twin_id),
            twin_external_id=r.twin.twin_external_id if r.twin else "unknown",
            inference_mode=r.inference_mode,
            status=r.status,
            responses=r.responses,
            summary_stats=r.summary_stats,
            created_at=r.created_at.isoformat(),
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
        )
        for r in runs
    ]


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
):
    """Generate a validation report from twin simulation results.

    Modes:
    - "synthesis": Analyze twin responses only (aggregate stats, T2B, composites, etc.)
    - "comparison": Compare twin responses against real participant M8 interview data
    """
    result = await db.execute(select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

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
