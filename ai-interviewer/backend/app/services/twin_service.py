"""Service layer for twin pipeline operations."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from app.models.twin import (
    DigitalTwin,
    Participant,
    PipelineJob,
    PipelineStepOutput,
    SimulationRun,
)


# ---------------------------------------------------------------------------
# Participant CRUD
# ---------------------------------------------------------------------------

async def create_participant(
    session: AsyncSession,
    *,
    external_id: str,
    profile_qa: list[dict],
    user_id: uuid.UUID | None = None,
    display_name: str | None = None,
    source: str = "interview",
    metadata: dict | None = None,
) -> Participant:
    participant = Participant(
        external_id=external_id,
        profile_qa=profile_qa,
        user_id=user_id,
        display_name=display_name,
        source=source,
        metadata_=metadata,
    )
    session.add(participant)
    await session.flush()
    return participant


async def get_participant(session: AsyncSession, participant_id: uuid.UUID) -> Participant | None:
    return await session.get(Participant, participant_id)


async def get_participant_by_external_id(session: AsyncSession, external_id: str) -> Participant | None:
    result = await session.execute(
        select(Participant).where(Participant.external_id == external_id)
    )
    return result.scalar_one_or_none()


async def get_participant_by_user_id(session: AsyncSession, user_id: uuid.UUID) -> Participant | None:
    result = await session.execute(
        select(Participant).where(Participant.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_participants(session: AsyncSession) -> list[Participant]:
    result = await session.execute(
        select(Participant).order_by(Participant.external_id)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Digital Twin CRUD
# ---------------------------------------------------------------------------

async def create_twin(
    session: AsyncSession,
    *,
    participant_id: uuid.UUID,
    twin_external_id: str,
    mode: str,
    profile_data: list[dict],
    combo_id: int | None = None,
    coherence_score: float | None = None,
    branch_choices: dict | None = None,
    profile_stats: dict | None = None,
    status: str = "building",
) -> DigitalTwin:
    twin = DigitalTwin(
        participant_id=participant_id,
        twin_external_id=twin_external_id,
        mode=mode,
        profile_data=profile_data,
        combo_id=combo_id,
        coherence_score=coherence_score,
        branch_choices=branch_choices,
        profile_stats=profile_stats,
        status=status,
    )
    session.add(twin)
    await session.flush()
    return twin


async def get_twin(session: AsyncSession, twin_id: uuid.UUID) -> DigitalTwin | None:
    return await session.get(DigitalTwin, twin_id)


async def get_twin_by_external_id(session: AsyncSession, external_id: str) -> DigitalTwin | None:
    result = await session.execute(
        select(DigitalTwin).where(DigitalTwin.twin_external_id == external_id)
    )
    return result.scalar_one_or_none()


async def get_twins_for_participant(session: AsyncSession, participant_id: uuid.UUID) -> list[DigitalTwin]:
    result = await session.execute(
        select(DigitalTwin)
        .where(DigitalTwin.participant_id == participant_id)
        .order_by(DigitalTwin.twin_external_id)
    )
    return list(result.scalars().all())


async def list_ready_twins(session: AsyncSession) -> list[DigitalTwin]:
    result = await session.execute(
        select(DigitalTwin)
        .where(DigitalTwin.status == "ready")
        .options(selectinload(DigitalTwin.participant))
        .order_by(DigitalTwin.twin_external_id)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Pipeline Job CRUD
# ---------------------------------------------------------------------------

async def create_job(
    session: AsyncSession,
    *,
    job_type: str,
    participant_id: uuid.UUID | None = None,
    study_id: uuid.UUID | None = None,
    config: dict | None = None,
    created_by: uuid.UUID | None = None,
) -> PipelineJob:
    job = PipelineJob(
        job_type=job_type,
        participant_id=participant_id,
        study_id=study_id,
        config=config,
        created_by=created_by,
    )
    session.add(job)
    await session.flush()
    return job


async def get_job(session: AsyncSession, job_id: uuid.UUID) -> PipelineJob | None:
    return await session.get(PipelineJob, job_id)


async def get_active_job_for_participant(
    session: AsyncSession, participant_id: uuid.UUID, job_type: str = "create_twin"
) -> PipelineJob | None:
    """Find a pending or running job for a participant."""
    result = await session.execute(
        select(PipelineJob).where(
            and_(
                PipelineJob.participant_id == participant_id,
                PipelineJob.job_type == job_type,
                PipelineJob.status.in_(["pending", "running"]),
            )
        )
    )
    return result.scalar_one_or_none()


async def get_active_simulation_job(
    session: AsyncSession, twin_id: uuid.UUID, study_id: uuid.UUID
) -> PipelineJob | None:
    """Find a pending or running simulation job for a specific twin + study."""
    result = await session.execute(
        select(PipelineJob).where(
            and_(
                PipelineJob.job_type == "run_simulation",
                PipelineJob.study_id == study_id,
                PipelineJob.status.in_(["pending", "running"]),
            )
        )
    )
    # Filter by twin via simulation_runs
    jobs = list(result.scalars().all())
    for job in jobs:
        sim = await session.execute(
            select(SimulationRun).where(
                and_(SimulationRun.job_id == job.id, SimulationRun.twin_id == twin_id)
            )
        )
        if sim.scalar_one_or_none():
            return job
    return None


async def update_job_status(
    session: AsyncSession,
    job_id: uuid.UUID,
    *,
    status: str | None = None,
    current_step: str | None = None,
    progress: dict | None = None,
    result_summary: dict | None = None,
    error_message: str | None = None,
    celery_task_id: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> PipelineJob | None:
    job = await session.get(PipelineJob, job_id)
    if not job:
        return None
    if status is not None:
        job.status = status
    if current_step is not None:
        job.current_step = current_step
    if progress is not None:
        job.progress = progress
    if result_summary is not None:
        job.result_summary = result_summary
    if error_message is not None:
        job.error_message = error_message
    if celery_task_id is not None:
        job.celery_task_id = celery_task_id
    if started_at is not None:
        job.started_at = started_at
    if completed_at is not None:
        job.completed_at = completed_at
    await session.flush()
    return job


# ---------------------------------------------------------------------------
# Pipeline Step Output CRUD
# ---------------------------------------------------------------------------

async def save_step_output(
    session: AsyncSession,
    *,
    participant_id: uuid.UUID,
    step_name: str,
    mode: str,
    output_data: dict | list,
    job_id: uuid.UUID | None = None,
    file_path: str | None = None,
) -> PipelineStepOutput:
    # Upsert: check if exists
    result = await session.execute(
        select(PipelineStepOutput).where(
            and_(
                PipelineStepOutput.participant_id == participant_id,
                PipelineStepOutput.step_name == step_name,
                PipelineStepOutput.mode == mode,
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.output_data = output_data
        existing.job_id = job_id
        existing.file_path = file_path
        await session.flush()
        return existing

    step_output = PipelineStepOutput(
        participant_id=participant_id,
        step_name=step_name,
        mode=mode,
        output_data=output_data,
        job_id=job_id,
        file_path=file_path,
    )
    session.add(step_output)
    await session.flush()
    return step_output


async def get_step_output(
    session: AsyncSession, participant_id: uuid.UUID, step_name: str, mode: str
) -> PipelineStepOutput | None:
    result = await session.execute(
        select(PipelineStepOutput).where(
            and_(
                PipelineStepOutput.participant_id == participant_id,
                PipelineStepOutput.step_name == step_name,
                PipelineStepOutput.mode == mode,
            )
        )
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Simulation Run CRUD
# ---------------------------------------------------------------------------

async def create_simulation_run(
    session: AsyncSession,
    *,
    twin_id: uuid.UUID,
    questionnaire_snapshot: dict,
    job_id: uuid.UUID | None = None,
    study_id: uuid.UUID | None = None,
    inference_mode: str = "combined",
) -> SimulationRun:
    run = SimulationRun(
        job_id=job_id,
        twin_id=twin_id,
        study_id=study_id,
        questionnaire_snapshot=questionnaire_snapshot,
        inference_mode=inference_mode,
    )
    session.add(run)
    await session.flush()
    return run


async def get_simulation_run(session: AsyncSession, run_id: uuid.UUID) -> SimulationRun | None:
    return await session.get(SimulationRun, run_id)


async def get_completed_simulation(
    session: AsyncSession, twin_id: uuid.UUID, study_id: uuid.UUID
) -> SimulationRun | None:
    """Find a completed simulation for a specific twin + study."""
    result = await session.execute(
        select(SimulationRun).where(
            and_(
                SimulationRun.twin_id == twin_id,
                SimulationRun.study_id == study_id,
                SimulationRun.status == "completed",
            )
        ).order_by(SimulationRun.created_at.desc())
    )
    return result.scalars().first()


async def list_simulations_for_study(session: AsyncSession, study_id: uuid.UUID) -> list[SimulationRun]:
    result = await session.execute(
        select(SimulationRun)
        .where(SimulationRun.study_id == study_id)
        .options(selectinload(SimulationRun.twin))
        .order_by(SimulationRun.created_at.desc())
    )
    return list(result.scalars().all())


async def update_simulation_run(
    session: AsyncSession,
    run_id: uuid.UUID,
    *,
    status: str | None = None,
    responses: list | None = None,
    summary_stats: dict | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> SimulationRun | None:
    run = await session.get(SimulationRun, run_id)
    if not run:
        return None
    if status is not None:
        run.status = status
    if responses is not None:
        run.responses = responses
    if summary_stats is not None:
        run.summary_stats = summary_stats
    if started_at is not None:
        run.started_at = started_at
    if completed_at is not None:
        run.completed_at = completed_at
    await session.flush()
    return run


# ---------------------------------------------------------------------------
# Sync variants for Celery tasks
# ---------------------------------------------------------------------------

def sync_get_participant(session: Session, participant_id: uuid.UUID) -> Participant | None:
    return session.get(Participant, participant_id)


def sync_get_step_output(
    session: Session, participant_id: uuid.UUID, step_name: str, mode: str
) -> PipelineStepOutput | None:
    result = session.execute(
        select(PipelineStepOutput).where(
            and_(
                PipelineStepOutput.participant_id == participant_id,
                PipelineStepOutput.step_name == step_name,
                PipelineStepOutput.mode == mode,
            )
        )
    )
    return result.scalar_one_or_none()


def sync_save_step_output(
    session: Session,
    *,
    participant_id: uuid.UUID,
    step_name: str,
    mode: str,
    output_data: dict | list,
    job_id: uuid.UUID | None = None,
    file_path: str | None = None,
) -> PipelineStepOutput:
    result = session.execute(
        select(PipelineStepOutput).where(
            and_(
                PipelineStepOutput.participant_id == participant_id,
                PipelineStepOutput.step_name == step_name,
                PipelineStepOutput.mode == mode,
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.output_data = output_data
        existing.job_id = job_id
        existing.file_path = file_path
        session.flush()
        return existing

    step_output = PipelineStepOutput(
        participant_id=participant_id,
        step_name=step_name,
        mode=mode,
        output_data=output_data,
        job_id=job_id,
        file_path=file_path,
    )
    session.add(step_output)
    session.flush()
    return step_output


def sync_update_job(
    session: Session,
    job_id: uuid.UUID,
    **kwargs,
) -> PipelineJob | None:
    job = session.get(PipelineJob, job_id)
    if not job:
        return None
    for key, value in kwargs.items():
        if value is not None and hasattr(job, key):
            setattr(job, key, value)
    session.flush()
    return job


def sync_create_twin(
    session: Session,
    *,
    participant_id: uuid.UUID,
    twin_external_id: str,
    mode: str,
    profile_data: list[dict],
    combo_id: int | None = None,
    coherence_score: float | None = None,
    branch_choices: dict | None = None,
    profile_stats: dict | None = None,
    status: str = "building",
) -> DigitalTwin:
    twin = DigitalTwin(
        participant_id=participant_id,
        twin_external_id=twin_external_id,
        mode=mode,
        profile_data=profile_data,
        combo_id=combo_id,
        coherence_score=coherence_score,
        branch_choices=branch_choices,
        profile_stats=profile_stats,
        status=status,
    )
    session.add(twin)
    session.flush()
    return twin


def sync_update_simulation_run(
    session: Session,
    run_id: uuid.UUID,
    **kwargs,
) -> SimulationRun | None:
    run = session.get(SimulationRun, run_id)
    if not run:
        return None
    for key, value in kwargs.items():
        if value is not None and hasattr(run, key):
            setattr(run, key, value)
    session.flush()
    return run
