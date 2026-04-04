"""Router for Step 4 — Questionnaire Builder endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.user import User
from app.schemas.questionnaire import SectionFeedbackRequest, SectionFeedbackResponse
from app.schemas.study import StepVersionResponse
from app.services.questionnaire_service import QuestionnaireService


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


def get_questionnaire_service() -> QuestionnaireService:
    """Dependency to get a QuestionnaireService singleton."""
    global _service
    if _service is None:
        _service = QuestionnaireService()
    return _service


@router.post("/steps/4/generate", response_model=StepVersionResponse)
async def generate_questionnaire(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: QuestionnaireService = Depends(get_questionnaire_service),
) -> StepVersionResponse:
    """Generate a questionnaire for the study.

    Requires step 3 to be locked. Loads all previous step outputs,
    calls the LLM with the questionnaire_generator prompt, and creates
    a new StepVersion for step 4 in 'review' status.
    """
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
async def submit_section_feedback(
    study_id: uuid.UUID,
    section_id: str,
    feedback: SectionFeedbackRequest,
    db: AsyncSession = Depends(get_session),
    service: QuestionnaireService = Depends(get_questionnaire_service),
) -> SectionFeedbackResponse:
    """Submit feedback for a specific section of the questionnaire.

    The section_id in the path must match the section_id in the request body.
    Step 4 must not be locked.
    """
    if feedback.section_id != section_id:
        raise HTTPException(
            status_code=400,
            detail=f"Path section_id '{section_id}' does not match "
                   f"body section_id '{feedback.section_id}'",
        )
    try:
        return await service.submit_section_feedback(study_id, feedback, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/steps/4/edit", response_model=StepVersionResponse)
async def edit_questionnaire(
    study_id: uuid.UUID,
    body: QuestionnaireEditRequest,
    db: AsyncSession = Depends(get_session),
    service: QuestionnaireService = Depends(get_questionnaire_service),
) -> StepVersionResponse:
    """Apply CRUD operations to the questionnaire.

    Accepts a list of operations: update_question, delete_question, add_question.
    Step 4 must not be locked.
    """
    try:
        return await service.edit_questionnaire(
            study_id, [op.model_dump() for op in body.operations], db
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/steps/4/lock", response_model=StepVersionResponse)
async def lock_questionnaire(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: QuestionnaireService = Depends(get_questionnaire_service),
    current_user: User = Depends(get_current_user),
) -> StepVersionResponse:
    """Lock step 4 and transition the study to 'complete'.

    Requires the study to be in step_4_review status.
    """
    try:
        return await service.lock_questionnaire(study_id, str(current_user.id), db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
