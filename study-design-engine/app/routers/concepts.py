"""Step 2 — Concept Board Builder API routes."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_study_owner
from app.database import get_session
from app.models.user import User
from app.schemas.concept import (
    ComparabilityCheckResponse,
    ConceptRefineResponse,
    ConceptResponse,
)
from sqlalchemy import select as sa_select

from app.models.study import Study
from app.schemas.study import StepVersionResponse
from app.services.concept_board_service import ConceptBoardService
from app.services.ad_creative_territory_service import AdCreativeTerritoryService
from app.services.ad_creative_product_brief_service import AdCreativeProductBriefService

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
_ad_service: AdCreativeTerritoryService | None = None
_pb_service: AdCreativeProductBriefService | None = None


def get_concept_service() -> ConceptBoardService:
    global _service
    if _service is None:
        _service = ConceptBoardService()
    return _service


def get_ad_creative_service() -> AdCreativeTerritoryService:
    global _ad_service
    if _ad_service is None:
        _ad_service = AdCreativeTerritoryService()
    return _ad_service


def get_product_brief_service() -> AdCreativeProductBriefService:
    global _pb_service
    if _pb_service is None:
        _pb_service = AdCreativeProductBriefService()
    return _pb_service


async def _is_ad_creative(study_id: uuid.UUID, db: AsyncSession) -> bool:
    """Check if study is ad_creative_testing."""
    result = await db.execute(sa_select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        return False
    return (study.study_metadata or {}).get("study_type") == "ad_creative_testing"


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


@router.post("/steps/2/generate")
async def generate_step_2(
    study_id: uuid.UUID,
    body: Optional[GenerateRequest] = None,
    db: AsyncSession = Depends(get_session),
    service: ConceptBoardService = Depends(get_concept_service),
    pb_service: AdCreativeProductBriefService = Depends(get_product_brief_service),
    current_user: User = Depends(get_current_user),
):
    """Generate Step 2.

    - concept_testing: generate N concept template records.
    - ad_creative_testing: generate a Product Brief draft from the Study Brief.
    """
    await require_study_owner(study_id, current_user, db)
    try:
        if await _is_ad_creative(study_id, db):
            return await pb_service.generate_product_brief(study_id, db)
        num = body.num_concepts if body else 3
        return await service.generate_templates(study_id, db, num_concepts=num)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/steps/2", response_model=StepVersionResponse)
async def edit_step_2(
    study_id: uuid.UUID,
    edits: dict,
    db: AsyncSession = Depends(get_session),
    pb_service: AdCreativeProductBriefService = Depends(get_product_brief_service),
    current_user: User = Depends(get_current_user),
):
    await require_study_owner(study_id, current_user, db)
    """Edit Step 2 content. Only applicable for ad_creative_testing (Product Brief).

    concept_testing edits concepts via /concepts/{id} PATCH endpoints.
    """
    if not await _is_ad_creative(study_id, db):
        raise HTTPException(
            status_code=400,
            detail="Step 2 PATCH is only supported for ad_creative_testing. "
                   "Edit concepts via /concepts/{id} instead.",
        )
    try:
        return await pb_service.edit_product_brief(study_id, edits, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/product-brief/refine")
async def refine_product_brief(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    pb_service: AdCreativeProductBriefService = Depends(get_product_brief_service),
    current_user: User = Depends(get_current_user),
):
    """Use the LLM to polish the user's current Product Brief text fields.

    Returns refined_fields (not persisted). The frontend shows suggestions and
    the user accepts/edits via the regular PATCH /steps/2 endpoint.
    """
    await require_study_owner(study_id, current_user, db)
    if not await _is_ad_creative(study_id, db):
        raise HTTPException(
            status_code=400,
            detail="Product Brief is only supported for ad_creative_testing studies.",
        )
    try:
        return await pb_service.refine_product_brief(study_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/steps/3/generate", response_model=list[ConceptResponse])
async def generate_territories_step_3(
    study_id: uuid.UUID,
    body: Optional[GenerateRequest] = None,
    db: AsyncSession = Depends(get_session),
    ad_service: AdCreativeTerritoryService = Depends(get_ad_creative_service),
    current_user: User = Depends(get_current_user),
):
    """Generate N empty creative territory templates. Only for ad_creative_testing."""
    await require_study_owner(study_id, current_user, db)
    if not await _is_ad_creative(study_id, db):
        raise HTTPException(
            status_code=404,
            detail="Step 3 generate is not available for this study type.",
        )
    num = body.num_concepts if body else 3
    try:
        return await ad_service.generate_territories(study_id, num, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/concepts/add", response_model=ConceptResponse)
async def add_concept(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: ConceptBoardService = Depends(get_concept_service),
    ad_service: AdCreativeTerritoryService = Depends(get_ad_creative_service),
    current_user: User = Depends(get_current_user),
):
    """Add a single new concept/territory to the study."""
    await require_study_owner(study_id, current_user, db)
    try:
        if await _is_ad_creative(study_id, db):
            return await ad_service.add_territory(study_id, db)
        return await service.add_concept(study_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/concepts/{concept_id}")
async def delete_concept(
    study_id: uuid.UUID,
    concept_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: ConceptBoardService = Depends(get_concept_service),
    ad_service: AdCreativeTerritoryService = Depends(get_ad_creative_service),
    current_user: User = Depends(get_current_user),
):
    """Delete a concept/territory. Step must not be locked."""
    await require_study_owner(study_id, current_user, db)
    try:
        if await _is_ad_creative(study_id, db):
            return await ad_service.delete_territory(study_id, concept_id, db)
        return await service.delete_concept(study_id, concept_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/concepts/{concept_id}", response_model=ConceptResponse)
async def update_concept(
    study_id: uuid.UUID,
    concept_id: uuid.UUID,
    body: UpdateConceptRequest,
    db: AsyncSession = Depends(get_session),
    service: ConceptBoardService = Depends(get_concept_service),
    ad_service: AdCreativeTerritoryService = Depends(get_ad_creative_service),
    current_user: User = Depends(get_current_user),
):
    """Update the raw components of a concept/territory."""
    await require_study_owner(study_id, current_user, db)
    try:
        if await _is_ad_creative(study_id, db):
            return await ad_service.update_territory(study_id, concept_id, body.components, db)
        return await service.update_concept(study_id, concept_id, body.components, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/concepts/{concept_id}/refine", response_model=ConceptRefineResponse)
async def refine_concept(
    study_id: uuid.UUID,
    concept_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: ConceptBoardService = Depends(get_concept_service),
    ad_service: AdCreativeTerritoryService = Depends(get_ad_creative_service),
    current_user: User = Depends(get_current_user),
):
    """Refine a concept/territory using the LLM."""
    await require_study_owner(study_id, current_user, db)
    try:
        if await _is_ad_creative(study_id, db):
            return await ad_service.refine_territory(study_id, concept_id, db)
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
    ad_service: AdCreativeTerritoryService = Depends(get_ad_creative_service),
    current_user: User = Depends(get_current_user),
):
    """Approve a concept's/territory's refined or brand-edited components."""
    await require_study_owner(study_id, current_user, db)
    try:
        if await _is_ad_creative(study_id, db):
            return await ad_service.approve_territory(study_id, concept_id, body.approved_components, db)
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
    current_user: User = Depends(get_current_user),
):
    """Run a comparability audit across all concepts."""
    await require_study_owner(study_id, current_user, db)
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
    current_user: User = Depends(get_current_user),
):
    """Generate a placeholder render image for a concept."""
    await require_study_owner(study_id, current_user, db)
    try:
        return await service.render_image(study_id, concept_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/steps/2/lock")
async def lock_step_2(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: ConceptBoardService = Depends(get_concept_service),
    pb_service: AdCreativeProductBriefService = Depends(get_product_brief_service),
    current_user: User = Depends(get_current_user),
):
    """Lock Step 2.

    - concept_testing: lock concept boards.
    - ad_creative_testing: lock the Product Brief.
    """
    await require_study_owner(study_id, current_user, db)
    try:
        if await _is_ad_creative(study_id, db):
            return await pb_service.lock_product_brief(study_id, str(current_user.id), db)
        return await service.lock_concepts(study_id, str(current_user.id), db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/steps/3/lock")
async def lock_step_3_territories(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    ad_service: AdCreativeTerritoryService = Depends(get_ad_creative_service),
    current_user: User = Depends(get_current_user),
):
    """Lock Step 3 (Territories). Only for ad_creative_testing."""
    await require_study_owner(study_id, current_user, db)
    if not await _is_ad_creative(study_id, db):
        raise HTTPException(
            status_code=404,
            detail="Step 3 lock is not available for this study type.",
        )
    try:
        return await ad_service.lock_territories(study_id, str(current_user.id), db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
