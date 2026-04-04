"""Admin API endpoints."""

import csv
import io
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_admin
from app.models.interview import InterviewModule, InterviewSession, InterviewTurn
from app.models.twin import DigitalTwin, Participant, PipelineJob
from app.models.user import User
from app.schemas.admin import (
    AdminModuleSummary,
    AdminUserListResponse,
    AdminUserSummary,
    CreateTwinRequest,
    CreateTwinResponse,
    JobStatusResponse,
    TranscriptModule,
    TranscriptResponse,
    TranscriptTurn,
    TwinStatusResponse,
    TwinSummary,
)
from app.services import twin_service

logger = logging.getLogger(__name__)

MODULE_NAMES = {
    "M1": "Core Identity & Context",
    "M2": "Preferences & Values",
    "M3": "Purchase Decision Logic",
    "M4": "Lifestyle & Grooming",
    "M5": "Sensory & Aesthetic Preferences",
    "M6": "Body Wash Deep-Dive",
    "M7": "Media & Influence",
    "M8": "Concept Test",
}

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List all users with module summary",
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(get_current_admin),
) -> AdminUserListResponse:
    """List all users with their module completion status."""
    # Total count
    count_result = await session.execute(select(func.count(User.id)))
    total_count = count_result.scalar_one()

    # Get users
    users_result = await session.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    users = users_result.scalars().all()

    summaries = []
    for user in users:
        # Get module statuses for this user
        mod_result = await session.execute(
            select(InterviewModule.module_id, InterviewModule.status)
            .join(InterviewSession, InterviewModule.session_id == InterviewSession.id)
            .where(InterviewSession.user_id == user.id)
        )
        mod_rows = mod_result.all()

        # Deduplicate: keep best status per module
        best_modules: dict[str, str] = {}
        for module_id, mod_status in mod_rows:
            if module_id not in best_modules:
                best_modules[module_id] = mod_status
            elif mod_status == "completed":
                best_modules[module_id] = "completed"

        modules = [
            AdminModuleSummary(module_id=mid, status=mstatus)
            for mid, mstatus in sorted(best_modules.items())
        ]

        # Count turns
        turn_count_result = await session.execute(
            select(func.count(InterviewTurn.id))
            .join(InterviewSession, InterviewTurn.session_id == InterviewSession.id)
            .where(InterviewSession.user_id == user.id)
        )
        total_turns = turn_count_result.scalar_one()

        # Check twin status
        participant = await twin_service.get_participant_by_user_id(session, user.id)
        twin_status_val = None
        if participant:
            twins = await twin_service.get_twins_for_participant(session, participant.id)
            if any(t.status == "ready" for t in twins):
                twin_status_val = "ready"
            elif twins:
                twin_status_val = "building"

        summaries.append(
            AdminUserSummary(
                user_id=str(user.id),
                email=user.email,
                display_name=user.display_name,
                sex=user.sex,
                age=user.age,
                created_at=user.created_at,
                modules=modules,
                completed_module_count=sum(
                    1 for m in modules if m.status == "completed"
                ),
                total_turns=total_turns,
                twin_status=twin_status_val,
            )
        )

    return AdminUserListResponse(
        users=summaries,
        total_count=total_count,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/users/{user_id}/transcript",
    response_model=TranscriptResponse,
    summary="Get full transcript for a user",
)
async def get_user_transcript(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(get_current_admin),
) -> TranscriptResponse:
    """Get full Q&A transcript for a user, grouped by module."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return await _build_transcript(session, user)


@router.get(
    "/users/{user_id}/transcript/download",
    summary="Download transcript as JSON or CSV",
)
async def download_transcript(
    user_id: UUID,
    format: str = Query("json", pattern="^(json|csv)$"),
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    """Download full transcript in JSON or CSV format."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    transcript = await _build_transcript(session, user)
    filename = f"transcript_{user.display_name.replace(' ', '_')}_{user_id}"

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["module_id", "module_name", "turn_index", "role", "question_text", "answer_text", "timestamp"]
        )
        for module in transcript.modules:
            for turn in module.turns:
                writer.writerow([
                    module.module_id,
                    module.module_name,
                    turn.turn_index,
                    turn.role,
                    turn.question_text or "",
                    turn.answer_text or "",
                    turn.created_at.isoformat(),
                ])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
        )
    else:
        data = transcript.model_dump(mode="json")
        return StreamingResponse(
            iter([json.dumps(data, indent=2, default=str)]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}.json"},
        )


@router.post(
    "/users/{user_id}/create-twin",
    response_model=CreateTwinResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create digital twin for a user",
)
async def create_twin(
    user_id: UUID,
    request: CreateTwinRequest,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(get_current_admin),
) -> CreateTwinResponse:
    """Trigger twin creation pipeline for a user who completed all modules."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check all 8 modules are completed
    mod_result = await session.execute(
        select(InterviewModule.module_id, InterviewModule.status)
        .join(InterviewSession, InterviewModule.session_id == InterviewSession.id)
        .where(InterviewSession.user_id == user.id)
    )
    mod_rows = mod_result.all()
    completed_modules = {mid for mid, mstatus in mod_rows if mstatus == "completed"}
    required = {"M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"}
    missing = required - completed_modules
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"User has not completed modules: {sorted(missing)}",
        )

    # Check if participant already exists
    participant = await twin_service.get_participant_by_user_id(session, user.id)

    if participant:
        # Check for existing ready twins matching the requested mode
        mode = "1to1" if request.n_twins == 1 else "branched"
        twins = await twin_service.get_twins_for_participant(session, participant.id)
        ready_twins = [t for t in twins if t.status == "ready" and t.mode == mode]
        if ready_twins:
            return CreateTwinResponse(
                job_id="existing",
                participant_id=str(participant.id),
                status="already_completed",
                status_url=f"/api/v1/admin/users/{user_id}/twin-status",
            )

        # Check for in-progress job
        active_job = await twin_service.get_active_job_for_participant(session, participant.id)
        if active_job:
            raise HTTPException(
                status_code=409,
                detail=f"Twin creation already in progress (job {active_job.id}, status: {active_job.status})",
            )
    else:
        # Extract QA pairs from interview turns
        turns_result = await session.execute(
            select(InterviewTurn)
            .join(InterviewSession, InterviewTurn.session_id == InterviewSession.id)
            .where(
                InterviewSession.user_id == user.id,
                InterviewTurn.role == "user",
                InterviewTurn.answer_text.isnot(None),
            )
            .order_by(InterviewTurn.module_id, InterviewTurn.turn_index)
        )
        turns = turns_result.scalars().all()

        # Build QA pairs, deduplicating by pairing with preceding interviewer turn
        qa_pairs = []
        for turn in turns:
            # Get the question from the preceding interviewer turn
            q_result = await session.execute(
                select(InterviewTurn)
                .where(
                    InterviewTurn.session_id == turn.session_id,
                    InterviewTurn.module_id == turn.module_id,
                    InterviewTurn.role == "interviewer",
                    InterviewTurn.turn_index < turn.turn_index,
                )
                .order_by(InterviewTurn.turn_index.desc())
                .limit(1)
            )
            q_turn = q_result.scalar_one_or_none()
            if q_turn and q_turn.question_text:
                qa_pairs.append({
                    "question_text": q_turn.question_text,
                    "answer_text": turn.answer_text,
                    "module_id": turn.module_id,
                })

        # Assign next external_id
        all_participants = await twin_service.list_participants(session)
        existing_nums = []
        for p in all_participants:
            try:
                existing_nums.append(int(p.external_id.replace("P", "")))
            except ValueError:
                pass
        next_num = max(existing_nums, default=0) + 1
        external_id = f"P{next_num:02d}"

        participant = await twin_service.create_participant(
            session,
            external_id=external_id,
            profile_qa=qa_pairs,
            user_id=user.id,
            display_name=user.display_name,
            source="interview",
        )

    # Create job and dispatch Celery task
    job = await twin_service.create_job(
        session,
        job_type="create_twin",
        participant_id=participant.id,
        config={"n_twins": request.n_twins},
        created_by=admin.id,
    )
    await session.commit()

    # Dispatch Celery task
    from app.tasks.twin_tasks import create_twin_pipeline
    create_twin_pipeline.delay(str(job.id), str(participant.id), request.n_twins)

    return CreateTwinResponse(
        job_id=str(job.id),
        participant_id=str(participant.id),
        status="pending",
        status_url=f"/api/v1/admin/users/{user_id}/twin-status",
    )


@router.get(
    "/users/{user_id}/twin-status",
    response_model=TwinStatusResponse,
    summary="Get twin creation status for a user",
)
async def get_twin_status(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(get_current_admin),
) -> TwinStatusResponse:
    """Get twin creation status for a user."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    participant = await twin_service.get_participant_by_user_id(session, user.id)
    if not participant:
        return TwinStatusResponse(
            participant_id=None,
            external_id=None,
            twins=[],
            latest_job=None,
        )

    twins = await twin_service.get_twins_for_participant(session, participant.id)
    twin_summaries = [
        TwinSummary(
            twin_id=str(t.id),
            twin_external_id=t.twin_external_id,
            mode=t.mode,
            coherence_score=t.coherence_score,
            status=t.status,
            created_at=t.created_at,
        )
        for t in twins
    ]

    # Get latest job
    job_result = await session.execute(
        select(PipelineJob)
        .where(
            PipelineJob.participant_id == participant.id,
            PipelineJob.job_type == "create_twin",
        )
        .order_by(PipelineJob.created_at.desc())
        .limit(1)
    )
    latest_job = job_result.scalar_one_or_none()
    job_info = None
    if latest_job:
        job_info = {
            "job_id": str(latest_job.id),
            "status": latest_job.status,
            "current_step": latest_job.current_step,
            "progress": latest_job.progress,
            "error_message": latest_job.error_message,
            "created_at": latest_job.created_at.isoformat() if latest_job.created_at else None,
            "started_at": latest_job.started_at.isoformat() if latest_job.started_at else None,
            "completed_at": latest_job.completed_at.isoformat() if latest_job.completed_at else None,
        }

    return TwinStatusResponse(
        participant_id=str(participant.id),
        external_id=participant.external_id,
        twins=twin_summaries,
        latest_job=job_info,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Get pipeline job status",
)
async def get_job_status(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(get_current_admin),
) -> JobStatusResponse:
    """Get status of a pipeline job."""
    job = await twin_service.get_job(session, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=str(job.id),
        job_type=job.job_type,
        status=job.status,
        current_step=job.current_step,
        progress=job.progress,
        result_summary=job.result_summary,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


async def _build_transcript(session: AsyncSession, user: User) -> TranscriptResponse:
    """Build a TranscriptResponse for a user."""
    # First, find the best session per module (prefer completed, then latest)
    mod_result = await session.execute(
        select(InterviewModule.module_id, InterviewModule.status, InterviewModule.session_id)
        .join(InterviewSession, InterviewModule.session_id == InterviewSession.id)
        .where(InterviewSession.user_id == user.id)
        .order_by(InterviewModule.module_id, InterviewModule.ended_at.desc().nulls_last())
    )
    mod_rows = mod_result.all()

    # Keep best session per module: completed > active > others
    best_sessions: dict[str, tuple[str, str]] = {}  # module_id -> (session_id, status)
    for module_id, mod_status, session_id in mod_rows:
        if module_id not in best_sessions:
            best_sessions[module_id] = (str(session_id), mod_status)
        elif mod_status == "completed" and best_sessions[module_id][1] != "completed":
            best_sessions[module_id] = (str(session_id), mod_status)

    if not best_sessions:
        return TranscriptResponse(
            user_id=str(user.id),
            display_name=user.display_name,
            email=user.email,
            sex=user.sex,
            age=user.age,
            modules=[],
            total_turns=0,
        )

    # Get turns only from the best sessions
    best_session_ids = [UUID(sid) for sid, _ in best_sessions.values()]
    result = await session.execute(
        select(InterviewTurn)
        .where(
            InterviewTurn.session_id.in_(best_session_ids),
        )
        .order_by(InterviewTurn.module_id, InterviewTurn.turn_index)
    )
    turns = result.scalars().all()

    # Group by module
    modules_map: dict[str, dict] = {}
    for turn in turns:
        mid = turn.module_id
        # Only include turns from the best session for this module
        best_sid, best_status = best_sessions.get(mid, (None, None))
        if best_sid and str(turn.session_id) != best_sid:
            continue
        if mid not in modules_map:
            modules_map[mid] = {
                "module_id": mid,
                "module_name": MODULE_NAMES.get(mid, mid),
                "status": best_status or "unknown",
                "turns": [],
            }
        modules_map[mid]["turns"].append(
            TranscriptTurn(
                turn_index=turn.turn_index,
                role=turn.role,
                question_text=turn.question_text,
                answer_text=turn.answer_text,
                module_id=mid,
                created_at=turn.created_at,
            )
        )

    modules = [
        TranscriptModule(**data)
        for data in sorted(modules_map.values(), key=lambda d: d["module_id"])
    ]

    total_turns = sum(len(m.turns) for m in modules)

    return TranscriptResponse(
        user_id=str(user.id),
        display_name=user.display_name,
        email=user.email,
        sex=user.sex,
        age=user.age,
        modules=modules,
        total_turns=total_turns,
    )
