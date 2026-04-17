"""Ad Creative Brief (Step 1) service — generate, edit, and lock for ad creative testing studies.

Mirrors StudyBriefService but uses the ad_creative_brief_generator prompt and
produces ad-creative-specific content (campaign_objective, kpi_modules, etc.).
Edit and lock logic is identical and inherited from the base pattern.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.study import Study, StepVersion
from app.models.metric import MetricLibrary
from app.schemas.study import StepVersionResponse
from app.services.audit_service import AuditService
from app.services.state_machine import StudyStateMachine
from app.services.prompt_service import PromptService
from app.llm.client import LLMClient


class AdCreativeBriefService:
    """Step 1 for ad_creative_testing studies."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        prompt_service: Optional[PromptService] = None,
    ):
        self.llm = llm_client or LLMClient()
        self.prompt_service = prompt_service or PromptService()

    async def generate_brief(
        self,
        study_id: uuid.UUID,
        db: AsyncSession,
    ) -> StepVersionResponse:
        study = await self._get_study(study_id, db)

        if study.status not in ("init", "step_1_draft"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot generate brief: study is in '{study.status}' status.",
            )

        # Load metric library
        metrics_result = await db.execute(select(MetricLibrary))
        metrics = metrics_result.scalars().all()
        metric_dicts = [
            {
                "id": m.id,
                "display_name": m.display_name,
                "category": m.category,
                "description": m.description,
                "applicable_study_types": m.applicable_study_types,
            }
            for m in metrics
        ]

        brand_context = study.context or {}
        context_parts = [
            f"- {k}: {v}" for k, v in brand_context.items()
            if k not in ("revenue_range", "previous_studies")
        ]
        additional_context = "\n".join(context_parts) if context_parts else "None provided"

        prompt = self.prompt_service.format_prompt(
            "ad_creative_brief_generator",
            metric_library_json=json.dumps(metric_dicts, indent=2),
            brand_name=study.brand_name or "Unknown",
            category=study.category or "General",
            additional_context=additional_context,
            brand_question=study.question,
        )

        try:
            brief_content = await self.llm.generate_json(prompt)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"LLM generation failed: {e}")

        # Ensure study_type is set
        brief_content["study_type"] = "ad_creative_testing"

        next_version = await self._next_version(study_id, 1, db)
        step_version = StepVersion(
            id=uuid.uuid4(),
            study_id=study_id,
            step=1,
            version=next_version,
            status="review",
            content=brief_content,
            ai_rationale={"source": "llm_generated", "model": self.llm.model},
            created_at=datetime.now(timezone.utc),
        )
        db.add(step_version)

        if study.status == "init":
            StudyStateMachine.transition(study, "step_1_draft")
        if study.status == "step_1_draft":
            StudyStateMachine.transition(study, "step_1_review")

        await db.commit()
        await db.refresh(step_version)

        await AuditService.log_event(
            study_id=study_id,
            action="step_1_generated",
            actor="system",
            payload={"version": next_version, "study_type": "ad_creative_testing"},
            db=db,
        )

        return StepVersionResponse.model_validate(step_version)

    # Edit and lock reuse the exact same logic as StudyBriefService
    # Import and delegate to avoid duplication

    async def edit_brief(self, study_id, edits, db):
        from app.services.study_brief_service import StudyBriefService
        svc = StudyBriefService(llm_client=self.llm, prompt_service=self.prompt_service)
        return await svc.edit_brief(study_id, edits, db)

    async def lock_brief(self, study_id, user_id, db):
        from app.services.study_brief_service import StudyBriefService
        svc = StudyBriefService(llm_client=self.llm, prompt_service=self.prompt_service)
        return await svc.lock_brief(study_id, user_id, db)

    # ── Helpers (same as StudyBriefService) ──

    @staticmethod
    async def _get_study(study_id, db):
        result = await db.execute(select(Study).where(Study.id == study_id))
        study = result.scalar_one_or_none()
        if not study:
            raise HTTPException(status_code=404, detail="Study not found")
        return study

    @staticmethod
    async def _next_version(study_id, step, db):
        result = await db.execute(
            select(sa_func.coalesce(sa_func.max(StepVersion.version), 0))
            .where(StepVersion.study_id == study_id, StepVersion.step == step)
        )
        return (result.scalar() or 0) + 1
