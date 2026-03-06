"""Router for Version History endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.study import StepVersionResponse
from app.services.version_history_service import VersionHistoryService

router = APIRouter(prefix="/api/v1/studies/{study_id}/steps", tags=["Versions"])


@router.get(
    "/{step}/versions",
    response_model=list[StepVersionResponse],
    summary="List versions for a step",
)
async def list_versions(
    study_id: uuid.UUID,
    step: int,
    db: AsyncSession = Depends(get_session),
):
    """Return all versions for a specific step of a study."""
    return await VersionHistoryService.get_versions(study_id, step, db)


@router.get(
    "/{step}/versions/{version}",
    response_model=StepVersionResponse,
    summary="Get specific version",
)
async def get_version(
    study_id: uuid.UUID,
    step: int,
    version: int,
    db: AsyncSession = Depends(get_session),
):
    """Return a specific step version by study, step, and version number."""
    return await VersionHistoryService.get_version(study_id, step, version, db)
