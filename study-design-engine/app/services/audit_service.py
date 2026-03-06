"""Audit logging service for tracking all study design actions."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.schemas.audit import AuditLogEntry


class AuditService:
    """Service for recording and querying audit log entries."""

    @staticmethod
    async def log_event(
        study_id: uuid.UUID,
        action: str,
        actor: str,
        payload: Optional[dict],
        db: AsyncSession,
    ) -> AuditLogEntry:
        """Record an audit event for a study.

        Args:
            study_id: The study this event relates to.
            action: Short action label, e.g. "step_1_generated".
            actor: Identifier of the user or system that performed the action.
            payload: Arbitrary JSON payload with event details.
            db: Async database session.

        Returns:
            AuditLogEntry schema of the created record.
        """
        now = datetime.now(timezone.utc)
        entry = AuditLog(
            id=uuid.uuid4(),
            study_id=study_id,
            action=action,
            actor=actor,
            payload=payload,
            created_at=now,
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return AuditLogEntry.model_validate(entry)

    @staticmethod
    async def get_study_audit(
        study_id: uuid.UUID,
        step: Optional[int],
        db: AsyncSession,
    ) -> list[AuditLogEntry]:
        """Retrieve audit log entries for a study, optionally filtered by step.

        Args:
            study_id: The study to query.
            step: If provided, filter to actions containing this step number.
            db: Async database session.

        Returns:
            List of AuditLogEntry schemas ordered by creation time descending.
        """
        query = (
            select(AuditLog)
            .where(AuditLog.study_id == study_id)
            .order_by(AuditLog.created_at.desc())
        )
        if step is not None:
            query = query.where(AuditLog.action.contains(f"step_{step}"))
        result = await db.execute(query)
        entries = result.scalars().all()
        return [AuditLogEntry.model_validate(e) for e in entries]
