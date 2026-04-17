"""Router for Research Design step.

- concept_testing: step 3 (after Concept Boards)
- ad_creative_testing: step 4 (after Territories, which is now step 3)

Both study types use the same ResearchDesignService, parameterized by step_number.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_study_owner
from app.database import get_session
from app.models.study import Study
from app.models.user import User
from app.schemas.study import StepVersionResponse
from app.services.research_design_service import ResearchDesignService

router = APIRouter(
    prefix="/api/v1/studies/{study_id}",
    tags=["Research Design"],
)


class EditRequest(BaseModel):
    edits: dict


async def _is_ad_creative(study_id: uuid.UUID, db: AsyncSession) -> bool:
    result = await db.execute(sa_select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        return False
    return (study.study_metadata or {}).get("study_type") == "ad_creative_testing"


# ───────────────────────────────────────────────────────
# /steps/3/* — concept_testing research design
# For ad_creative, /steps/3/* is Territories (handled in concepts.py)
# ───────────────────────────────────────────────────────


@router.post("/steps/3/generate", response_model=StepVersionResponse)
async def generate_step_3(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate Step 3 — Research Design (concept_testing only)."""
    await require_study_owner(study_id, current_user, db)
    if await _is_ad_creative(study_id, db):
        raise HTTPException(
            status_code=404,
            detail="Step 3 is Territories for ad_creative_testing (see /steps/3/generate in concepts router).",
        )
    service = ResearchDesignService(step_number=3)
    try:
        return await service.generate_design(study_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/steps/3", response_model=StepVersionResponse)
async def edit_step_3(
    study_id: uuid.UUID,
    body: EditRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await require_study_owner(study_id, current_user, db)
    if await _is_ad_creative(study_id, db):
        raise HTTPException(status_code=404, detail="Step 3 edit not applicable for ad_creative_testing.")
    service = ResearchDesignService(step_number=3)
    try:
        return await service.edit_design(study_id, body.edits, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/steps/3/lock", response_model=StepVersionResponse)
async def lock_step_3_research_design(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await require_study_owner(study_id, current_user, db)
    if await _is_ad_creative(study_id, db):
        raise HTTPException(status_code=404, detail="Step 3 lock for ad_creative is in concepts router (Territories).")
    service = ResearchDesignService(step_number=3)
    try:
        return await service.lock_design(study_id, str(current_user.id), db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ───────────────────────────────────────────────────────
# /steps/4/* — ad_creative_testing research design
# For concept_testing, /steps/4/* is Questionnaire (handled in questionnaire.py)
# ───────────────────────────────────────────────────────


@router.post("/steps/4/generate", response_model=StepVersionResponse)
async def generate_step_4_research_design(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate Step 4 — Research Design (ad_creative_testing only)."""
    await require_study_owner(study_id, current_user, db)
    if not await _is_ad_creative(study_id, db):
        # For concept_testing, /steps/4/* is Questionnaire (other router)
        raise HTTPException(
            status_code=404,
            detail="Step 4 research design is only for ad_creative_testing. concept_testing uses /steps/4 for Questionnaire.",
        )
    service = ResearchDesignService(step_number=4)
    try:
        return await service.generate_design(study_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/steps/4", response_model=StepVersionResponse)
async def edit_step_4_research_design(
    study_id: uuid.UUID,
    body: EditRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await require_study_owner(study_id, current_user, db)
    if not await _is_ad_creative(study_id, db):
        raise HTTPException(status_code=404, detail="Step 4 research design PATCH only for ad_creative_testing.")
    service = ResearchDesignService(step_number=4)
    try:
        return await service.edit_design(study_id, body.edits, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/steps/4/lock", response_model=StepVersionResponse)
async def lock_step_4_research_design(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await require_study_owner(study_id, current_user, db)
    if not await _is_ad_creative(study_id, db):
        raise HTTPException(status_code=404, detail="Step 4 lock for concept_testing is in questionnaire router.")
    service = ResearchDesignService(step_number=4)
    try:
        return await service.lock_design(study_id, str(current_user.id), db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
