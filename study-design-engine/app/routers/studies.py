"""Router for Study Brief (Step 1) endpoints — generate, edit, lock."""

import uuid
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_study_owner
from app.database import get_session
from app.models.user import User
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession as AsyncDB

from app.llm.client import get_llm_client, LLMClient
from app.models.study import Study
from app.schemas.study import StepVersionResponse
from app.services.prompt_service import get_prompt_service, PromptService
from app.services.study_brief_service import StudyBriefService
from app.services.ad_creative_brief_service import AdCreativeBriefService

router = APIRouter(prefix="/api/v1/studies", tags=["Studies"])


async def _get_study_type(study_id: uuid.UUID, db: AsyncDB) -> str:
    """Read study_type from study_metadata."""
    result = await db.execute(sa_select(Study).where(Study.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        return "concept_testing"
    return (study.study_metadata or {}).get("study_type", "concept_testing")


def _get_brief_service(
    llm: LLMClient = Depends(get_llm_client),
    prompt_svc: PromptService = Depends(get_prompt_service),
) -> StudyBriefService:
    return StudyBriefService(llm_client=llm, prompt_service=prompt_svc)


def _get_ad_creative_brief_service(
    llm: LLMClient = Depends(get_llm_client),
    prompt_svc: PromptService = Depends(get_prompt_service),
) -> AdCreativeBriefService:
    return AdCreativeBriefService(llm_client=llm, prompt_service=prompt_svc)


@router.post(
    "/{study_id}/steps/1/generate",
    response_model=StepVersionResponse,
    summary="Generate a study brief (Step 1)",
)
async def generate_brief(
    study_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    service: StudyBriefService = Depends(_get_brief_service),
    ad_service: AdCreativeBriefService = Depends(_get_ad_creative_brief_service),
    current_user: User = Depends(get_current_user),
):
    """Use the LLM to generate a study brief for the given study.

    Dispatches to the ad creative brief service if study_type is ad_creative_testing.
    """
    await require_study_owner(study_id, current_user, db)
    study_type = await _get_study_type(study_id, db)
    if study_type == "ad_creative_testing":
        return await ad_service.generate_brief(study_id, db)
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
    current_user: User = Depends(get_current_user),
):
    """Apply manual edits to the latest Step 1 version, creating a new version.

    The step must not be locked.
    """
    await require_study_owner(study_id, current_user, db)
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
    await require_study_owner(study_id, current_user, db)
    return await service.lock_brief(study_id, str(current_user.id), db)
