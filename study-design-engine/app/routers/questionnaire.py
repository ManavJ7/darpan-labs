"""Router for Questionnaire Builder endpoints.

- concept_testing: step 4 (after Research Design at step 3)
- ad_creative_testing: step 5 (after Research Design at step 4, which follows the new Product Brief → Territories → Research Design flow)
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_study_owner
from app.database import get_session
from app.models.study import Study
from app.models.user import User
from app.schemas.questionnaire import SectionFeedbackRequest, SectionFeedbackResponse
from app.schemas.study import StepVersionResponse
from app.services.questionnaire_service import QuestionnaireService
from app.services.ad_creative_questionnaire_service import AdCreativeQuestionnaireService


class QuestionnaireEditOperation(BaseModel):
    type: str  # "update_question" | "delete_question" | "add_question"
    question_id: str | None = None
    section_id: str | None = None
    updates: dict[str, Any] | None = None
    question: dict[str, Any] | None = None


class QuestionnaireEditRequest(BaseModel):
    operations: list[QuestionnaireEditOperation]


router = APIRouter(
    prefix="/api/v1/studies/{study_id}",
    tags=["Questionnaire"],
)

_service: QuestionnaireService | None = None
_ad_service: AdCreativeQuestionnaireService | None = None


def get_questionnaire_service() -> QuestionnaireService:
    global _service
    if _service is None:
        _service = QuestionnaireService()
    return _service


def get_ad_questionnaire_service() -> AdCreativeQuestionnaireService:
    global _ad_service
    if _ad_service is None:
        _ad_service = AdCreativeQuestionnaireService()
    return _ad_service


async def _is_ad_creative(study_id: uuid.UUID, db: AsyncSession) -> bool:
    result = await db.execute(sa_select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        return False
    return (study.study_metadata or {}).get("study_type") == "ad_creative_testing"


# ───────────────────────────────────────────────────────
# /steps/4/* — concept_testing questionnaire
# For ad_creative, /steps/4/* is Research Design (handled in research_design.py)
# ───────────────────────────────────────────────────────


@router.post("/steps/4/generate", response_model=StepVersionResponse)
async def generate_step_4_questionnaire(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: QuestionnaireService = Depends(get_questionnaire_service),
    current_user: User = Depends(get_current_user),
) -> StepVersionResponse:
    """Generate Step 4 Questionnaire (concept_testing only)."""
    await require_study_owner(study_id, current_user, db)
    if await _is_ad_creative(study_id, db):
        raise HTTPException(
            status_code=404,
            detail="For ad_creative_testing, Step 4 is Research Design. Use /steps/5/generate for Questionnaire.",
        )
    try:
        return await service.generate_questionnaire(study_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Questionnaire generation failed: {str(exc)}")


@router.post(
    "/steps/4/sections/{section_id}/feedback",
    response_model=SectionFeedbackResponse,
)
async def submit_section_feedback_step_4(
    study_id: uuid.UUID,
    section_id: str,
    feedback: SectionFeedbackRequest,
    db: AsyncSession = Depends(get_session),
    service: QuestionnaireService = Depends(get_questionnaire_service),
    current_user: User = Depends(get_current_user),
) -> SectionFeedbackResponse:
    await require_study_owner(study_id, current_user, db)
    if await _is_ad_creative(study_id, db):
        raise HTTPException(status_code=404, detail="For ad_creative, use /steps/5/sections/{section_id}/feedback")
    if feedback.section_id != section_id:
        raise HTTPException(status_code=400, detail="Path and body section_id mismatch")
    try:
        return await service.submit_section_feedback(study_id, feedback, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/steps/4/edit", response_model=StepVersionResponse)
async def edit_step_4_questionnaire(
    study_id: uuid.UUID,
    body: QuestionnaireEditRequest,
    db: AsyncSession = Depends(get_session),
    service: QuestionnaireService = Depends(get_questionnaire_service),
    current_user: User = Depends(get_current_user),
) -> StepVersionResponse:
    await require_study_owner(study_id, current_user, db)
    if await _is_ad_creative(study_id, db):
        raise HTTPException(status_code=404, detail="For ad_creative, use /steps/5/edit")
    try:
        return await service.edit_questionnaire(
            study_id, [op.model_dump() for op in body.operations], db
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/steps/4/lock", response_model=StepVersionResponse)
async def lock_step_4(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: QuestionnaireService = Depends(get_questionnaire_service),
    current_user: User = Depends(get_current_user),
) -> StepVersionResponse:
    """Lock Step 4 — Questionnaire (concept_testing) or Research Design (ad_creative).

    For ad_creative_testing, this is not a questionnaire lock; the research_design
    router handles /steps/4/lock for ad_creative. This endpoint 404s for ad_creative.
    """
    await require_study_owner(study_id, current_user, db)
    if await _is_ad_creative(study_id, db):
        raise HTTPException(
            status_code=404,
            detail="For ad_creative_testing, /steps/4/lock is Research Design lock (research_design router).",
        )
    try:
        return await service.lock_questionnaire(study_id, str(current_user.id), db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ───────────────────────────────────────────────────────
# /steps/5/* — ad_creative_testing questionnaire
# ───────────────────────────────────────────────────────


@router.post("/steps/5/generate", response_model=StepVersionResponse)
async def generate_step_5_questionnaire(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: AdCreativeQuestionnaireService = Depends(get_ad_questionnaire_service),
    current_user: User = Depends(get_current_user),
) -> StepVersionResponse:
    """Generate Step 5 Questionnaire (ad_creative_testing only)."""
    await require_study_owner(study_id, current_user, db)
    if not await _is_ad_creative(study_id, db):
        raise HTTPException(status_code=404, detail="Step 5 is only for ad_creative_testing.")
    try:
        return await service.generate_questionnaire(study_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Questionnaire generation failed: {str(exc)}")


@router.post(
    "/steps/5/sections/{section_id}/feedback",
    response_model=SectionFeedbackResponse,
)
async def submit_section_feedback_step_5(
    study_id: uuid.UUID,
    section_id: str,
    feedback: SectionFeedbackRequest,
    db: AsyncSession = Depends(get_session),
    service: AdCreativeQuestionnaireService = Depends(get_ad_questionnaire_service),
    current_user: User = Depends(get_current_user),
) -> SectionFeedbackResponse:
    await require_study_owner(study_id, current_user, db)
    if not await _is_ad_creative(study_id, db):
        raise HTTPException(status_code=404, detail="Step 5 is only for ad_creative_testing.")
    if feedback.section_id != section_id:
        raise HTTPException(status_code=400, detail="Path and body section_id mismatch")
    try:
        return await service.submit_section_feedback(study_id, section_id, feedback, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/steps/5/edit", response_model=StepVersionResponse)
async def edit_step_5_questionnaire(
    study_id: uuid.UUID,
    body: QuestionnaireEditRequest,
    db: AsyncSession = Depends(get_session),
    service: AdCreativeQuestionnaireService = Depends(get_ad_questionnaire_service),
    current_user: User = Depends(get_current_user),
) -> StepVersionResponse:
    await require_study_owner(study_id, current_user, db)
    if not await _is_ad_creative(study_id, db):
        raise HTTPException(status_code=404, detail="Step 5 is only for ad_creative_testing.")
    try:
        return await service.edit_questionnaire(
            study_id, [op.model_dump() for op in body.operations], db
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/steps/5/lock", response_model=StepVersionResponse)
async def lock_step_5(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: AdCreativeQuestionnaireService = Depends(get_ad_questionnaire_service),
    current_user: User = Depends(get_current_user),
) -> StepVersionResponse:
    """Lock Step 5 — Questionnaire (ad_creative_testing only)."""
    await require_study_owner(study_id, current_user, db)
    if not await _is_ad_creative(study_id, db):
        raise HTTPException(status_code=404, detail="Step 5 is only for ad_creative_testing.")
    try:
        return await service.lock_questionnaire(study_id, str(current_user.id), db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
