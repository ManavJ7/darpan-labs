"""Step 2 — Concept Board Builder API routes."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.user import User
from app.schemas.concept import (
    ComparabilityCheckResponse,
    ConceptRefineResponse,
    ConceptResponse,
)
from app.services.concept_board_service import ConceptBoardService

router = APIRouter(
    prefix="/api/v1/studies/{study_id}",
    tags=["Concepts"],
)


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    num_concepts: int = 3


class UpdateConceptRequest(BaseModel):
    components: dict


class ApproveConceptRequest(BaseModel):
    approved_components: dict


# ---------------------------------------------------------------------------
# Dependency — service singleton
# ---------------------------------------------------------------------------

_service: ConceptBoardService | None = None


def get_concept_service() -> ConceptBoardService:
    global _service
    if _service is None:
        _service = ConceptBoardService()
    return _service


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/concepts", response_model=list[ConceptResponse])
async def list_concepts(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: ConceptBoardService = Depends(get_concept_service),
):
    """List all concepts for a study."""
    try:
        return await service.list_concepts(study_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/steps/2/generate", response_model=list[ConceptResponse])
async def generate_templates(
    study_id: uuid.UUID,
    body: Optional[GenerateRequest] = None,
    db: AsyncSession = Depends(get_session),
    service: ConceptBoardService = Depends(get_concept_service),
):
    """Generate N empty concept template records for a study."""
    num = body.num_concepts if body else 3
    try:
        return await service.generate_templates(study_id, db, num_concepts=num)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/concepts/add", response_model=ConceptResponse)
async def add_concept(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: ConceptBoardService = Depends(get_concept_service),
):
    """Add a single new concept board to the study."""
    try:
        return await service.add_concept(study_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/concepts/{concept_id}", response_model=ConceptResponse)
async def update_concept(
    study_id: uuid.UUID,
    concept_id: uuid.UUID,
    body: UpdateConceptRequest,
    db: AsyncSession = Depends(get_session),
    service: ConceptBoardService = Depends(get_concept_service),
):
    """Update the raw components of a concept."""
    try:
        return await service.update_concept(study_id, concept_id, body.components, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/concepts/{concept_id}/refine", response_model=ConceptRefineResponse)
async def refine_concept(
    study_id: uuid.UUID,
    concept_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: ConceptBoardService = Depends(get_concept_service),
):
    """Refine a concept using the LLM."""
    try:
        return await service.refine_concept(study_id, concept_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/concepts/{concept_id}/approve", response_model=ConceptResponse)
async def approve_concept(
    study_id: uuid.UUID,
    concept_id: uuid.UUID,
    body: ApproveConceptRequest,
    db: AsyncSession = Depends(get_session),
    service: ConceptBoardService = Depends(get_concept_service),
):
    """Approve a concept's refined or brand-edited components."""
    try:
        return await service.approve_concept(
            study_id, concept_id, body.approved_components, db
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/concepts/comparability-check", response_model=ComparabilityCheckResponse)
async def comparability_check(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: ConceptBoardService = Depends(get_concept_service),
):
    """Run a comparability audit across all concepts."""
    try:
        return await service.comparability_check(study_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/concepts/{concept_id}/render", response_model=ConceptResponse)
async def render_image(
    study_id: uuid.UUID,
    concept_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: ConceptBoardService = Depends(get_concept_service),
):
    """Generate a placeholder render image for a concept."""
    try:
        return await service.render_image(study_id, concept_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/steps/2/lock")
async def lock_concepts(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: ConceptBoardService = Depends(get_concept_service),
    current_user: User = Depends(get_current_user),
):
    """Lock step 2 after all concepts are approved."""
    try:
        return await service.lock_concepts(study_id, str(current_user.id), db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
