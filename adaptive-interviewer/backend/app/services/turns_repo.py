"""DB access helpers for interview turns — kept small and typed so
the orchestrator code stays readable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InterviewSession, InterviewTurn
from app.services.state_machine import TurnRecord


async def load_session(db: AsyncSession, session_id: UUID) -> Optional[InterviewSession]:
    res = await db.execute(select(InterviewSession).where(InterviewSession.id == session_id))
    return res.scalar_one_or_none()


async def load_turns(db: AsyncSession, session_id: UUID) -> list[InterviewTurn]:
    res = await db.execute(
        select(InterviewTurn)
        .where(InterviewTurn.session_id == session_id)
        .order_by(InterviewTurn.turn_index.asc())
    )
    return list(res.scalars().all())


def to_records(turns: list[InterviewTurn]) -> list[TurnRecord]:
    records: list[TurnRecord] = []
    for t in turns:
        meta = t.question_meta or t.answer_meta or {}
        records.append(
            TurnRecord(
                module_code=t.module_id,
                role=t.role,
                probe_index=int(meta.get("probe_index", 0)),
                item_satisfied=bool(meta.get("item_satisfied", False)),
                answer_text=t.answer_text,
                answer_structured=t.answer_structured,
            )
        )
    return records


async def next_turn_index(db: AsyncSession, session_id: UUID) -> int:
    turns = await load_turns(db, session_id)
    return len(turns)


async def record_interviewer_turn(
    db: AsyncSession,
    *,
    session_id: UUID,
    module_code: str,
    turn_index: int,
    question_text: str,
    phase_id: str,
    probe_index: int,
    item_satisfied: bool,
    widget: Optional[dict] = None,
    extra_meta: Optional[dict] = None,
) -> InterviewTurn:
    meta = {
        "phase_id": phase_id,
        "probe_index": probe_index,
        "item_satisfied": item_satisfied,
        "widget": widget,
    }
    if extra_meta:
        meta.update(extra_meta)
    turn = InterviewTurn(
        session_id=session_id,
        module_id=module_code,
        turn_index=turn_index,
        role="interviewer",
        input_mode="text",
        question_text=question_text,
        question_meta=meta,
    )
    db.add(turn)
    await db.flush()
    return turn


async def record_user_turn(
    db: AsyncSession,
    *,
    session_id: UUID,
    module_code: str,
    turn_index: int,
    answer_text: Optional[str],
    answer_structured: Optional[dict],
    client_meta: Optional[dict] = None,
) -> InterviewTurn:
    turn = InterviewTurn(
        session_id=session_id,
        module_id=module_code,
        turn_index=turn_index,
        role="user",
        input_mode="text",
        answer_text=answer_text,
        answer_structured=answer_structured,
        answer_meta={
            "client_meta": client_meta or {},
            "received_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.add(turn)
    await db.flush()
    return turn
