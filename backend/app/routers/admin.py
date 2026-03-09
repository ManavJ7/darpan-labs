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
from app.models.user import User
from app.schemas.admin import (
    AdminModuleSummary,
    AdminUserListResponse,
    AdminUserSummary,
    TranscriptModule,
    TranscriptResponse,
    TranscriptTurn,
)

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
