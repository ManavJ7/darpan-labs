"""Router for Step 3 — Research Design Document."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.user import User
from app.schemas.study import StepVersionResponse
from app.services.research_design_service import ResearchDesignService

router = APIRouter(
    prefix="/api/v1/studies/{study_id}",
    tags=["Research Design"],
)


class EditRequest(BaseModel):
    edits: dict


def _get_service() -> ResearchDesignService:
    return ResearchDesignService()


@router.post("/steps/3/generate", response_model=StepVersionResponse)
async def generate_research_design(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: ResearchDesignService = Depends(_get_service),
):
    """Generate a new Step 3 Research Design Document for the study."""
    try:
        return await service.generate_design(study_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/steps/3", response_model=StepVersionResponse)
async def edit_research_design(
    study_id: uuid.UUID,
    body: EditRequest,
    db: AsyncSession = Depends(get_session),
    service: ResearchDesignService = Depends(_get_service),
):
    """Edit the current Step 3 Research Design and recalculate affected fields."""
    try:
        return await service.edit_design(study_id, body.edits, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/steps/3/lock", response_model=StepVersionResponse)
async def lock_research_design(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: ResearchDesignService = Depends(_get_service),
    current_user: User = Depends(get_current_user),
):
    """Lock Step 3 — freeze the research design."""
    try:
        return await service.lock_design(study_id, str(current_user.id), db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
