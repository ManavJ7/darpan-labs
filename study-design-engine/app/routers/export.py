"""Router for Study Export endpoint."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.study_export_service import StudyExportService

router = APIRouter(prefix="/api/v1/studies/{study_id}", tags=["Export"])


@router.get("/export", summary="Export full study")
async def export_study(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """Export the complete study design as a single nested JSON document."""
    return await StudyExportService.export_study(study_id, db)
