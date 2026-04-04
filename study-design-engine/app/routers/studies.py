"""Router for Study Brief (Step 1) endpoints — generate, edit, lock."""

import uuid
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.user import User
from app.llm.client import get_llm_client, LLMClient
from app.schemas.study import StepVersionResponse
from app.services.prompt_service import get_prompt_service, PromptService
from app.services.study_brief_service import StudyBriefService

router = APIRouter(prefix="/api/v1/studies", tags=["Studies"])


def _get_brief_service(
    llm: LLMClient = Depends(get_llm_client),
    prompt_svc: PromptService = Depends(get_prompt_service),
) -> StudyBriefService:
    return StudyBriefService(llm_client=llm, prompt_service=prompt_svc)


@router.post(
    "/{study_id}/steps/1/generate",
    response_model=StepVersionResponse,
    summary="Generate a study brief (Step 1)",
)
async def generate_brief(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: StudyBriefService = Depends(_get_brief_service),
):
    """Use the LLM to generate a study brief for the given study.

    The study must be in 'init' or 'step_1_draft' status.
    """
    return await service.generate_brief(study_id, db)


@router.patch(
    "/{study_id}/steps/1",
    response_model=StepVersionResponse,
    summary="Edit the study brief (Step 1)",
)
async def edit_brief(
    study_id: uuid.UUID,
    edits: dict = Body(...),
    db: AsyncSession = Depends(get_session),
    service: StudyBriefService = Depends(_get_brief_service),
):
    """Apply manual edits to the latest Step 1 version, creating a new version.

    The step must not be locked.
    """
    return await service.edit_brief(study_id, edits, db)


@router.post(
    "/{study_id}/steps/1/lock",
    response_model=StepVersionResponse,
    summary="Lock the study brief (Step 1)",
)
async def lock_brief(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: StudyBriefService = Depends(_get_brief_service),
    current_user: User = Depends(get_current_user),
):
    """Lock Step 1, preventing further edits.

    The study must be in 'step_1_review' status.
    """
    return await service.lock_brief(study_id, str(current_user.id), db)
