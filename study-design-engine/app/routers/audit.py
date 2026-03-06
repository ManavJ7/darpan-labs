"""Router for Audit Log endpoints."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.audit import AuditLogEntry
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/studies/{study_id}/audit-log", tags=["Audit"])


@router.get("/", response_model=list[AuditLogEntry], summary="Get audit log")
async def get_audit_log(
    study_id: uuid.UUID,
    step: Optional[int] = Query(None, description="Filter by step number"),
    db: AsyncSession = Depends(get_session),
):
    """Return audit log entries for a study, optionally filtered by step."""
    return await AuditService.get_study_audit(study_id, step, db)
