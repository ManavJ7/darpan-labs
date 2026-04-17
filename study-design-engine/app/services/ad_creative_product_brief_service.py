"""Product Brief (Step 2) service — user-authored, AI-refined.

Pattern:
- generate_product_brief: creates an EMPTY template. User fills it in via edit_product_brief.
- refine_product_brief: LLM polishes the user's text (does not invent).
- edit_product_brief: user edits any field.
- lock_product_brief: finalizes.

Stored as StepVersion with step=2 for ad_creative_testing.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.study import Study, StepVersion
from app.schemas.study import StepVersionResponse
from app.services.audit_service import AuditService
from app.services.state_machine import StudyStateMachine
from app.services.prompt_service import PromptService
from app.llm.client import LLMClient


def _empty_product_brief() -> dict:
    return {
        "product_name": "",
        "category": "",
        "target_audience_description": "",
        "key_features": [],
        "key_differentiator": "",
        "must_communicate": "",
    }


class AdCreativeProductBriefService:
    """Step 2 for ad_creative_testing studies — Product Brief."""

    STEP = 2

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        prompt_service: Optional[PromptService] = None,
    ):
        self.llm = llm_client or LLMClient()
        self.prompt_service = prompt_service or PromptService()

    async def generate_product_brief(
        self,
        study_id: uuid.UUID,
        db: AsyncSession,
    ) -> StepVersionResponse:
        """Create an EMPTY Product Brief template. No LLM call.

        User will fill in fields via edit_product_brief, then optionally
        call refine_product_brief to polish.
        """
        study = await self._get_study(study_id, db)

        if not StudyStateMachine.can_start_step(study, self.STEP):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot start Product Brief: study is in '{study.status}' status. "
                       f"Lock Step 1 (Study Brief) first.",
            )

        # Pre-fill category from the study's category if available
        content = _empty_product_brief()
        if study.category:
            content["category"] = study.category

        next_version = await self._next_version(study_id, self.STEP, db)
        step_version = StepVersion(
            id=uuid.uuid4(),
            study_id=study_id,
            step=self.STEP,
            version=next_version,
            status="review",
            content=content,
            ai_rationale={"source": "empty_template"},
            created_at=datetime.now(timezone.utc),
        )
        db.add(step_version)

        if study.status == "step_1_locked":
            StudyStateMachine.transition(study, "step_2_draft")
        if study.status == "step_2_draft":
            StudyStateMachine.transition(study, "step_2_review")

        await db.commit()
        await db.refresh(step_version)

        await AuditService.log_event(
            study_id=study_id,
            action="product_brief_template_created",
            actor="system",
            payload={"version": next_version},
            db=db,
        )

        return StepVersionResponse.model_validate(step_version)

    async def refine_product_brief(
        self,
        study_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict:
        """Run the LLM on the current Product Brief to polish text fields.

        Returns the refined_fields dict; does NOT persist changes.
        The frontend shows the refined version and the user accepts/edits.
        """
        study = await self._get_study(study_id, db)

        if StudyStateMachine.is_step_locked(study, self.STEP):
            raise HTTPException(
                status_code=409,
                detail="Step 2 (Product Brief) is locked and cannot be refined.",
            )

        latest = await self._get_latest_version(study_id, self.STEP, db)
        if latest is None:
            raise HTTPException(
                status_code=404,
                detail="No Product Brief exists yet. Generate an empty template first.",
            )

        content = latest.content or {}

        # Load Study Brief for context
        step1 = await self._get_locked_step(study_id, 1, db)
        study_brief_content = step1.content if step1 else {}

        prompt = self.prompt_service.format_prompt(
            "ad_creative_product_brief_refiner",
            study_brief_json=json.dumps(study_brief_content, indent=2),
            brand_name=study.brand_name or "Unknown",
            category=study.category or "General",
            product_name=content.get("product_name", "") or "",
            product_category=content.get("category", "") or "",
            target_audience_description=content.get("target_audience_description", "") or "",
            key_features=", ".join(content.get("key_features", []) or []),
            key_differentiator=content.get("key_differentiator", "") or "",
            must_communicate=content.get("must_communicate", "") or "",
        )

        try:
            result = await self.llm.generate_json(prompt)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"LLM refinement failed: {e}")

        await AuditService.log_event(
            study_id=study_id,
            action="product_brief_refined",
            actor="system",
            payload={"fields_refined": list(result.get("refined_fields", {}).keys())},
            db=db,
        )

        return result

    async def edit_product_brief(
        self,
        study_id: uuid.UUID,
        edits: dict,
        db: AsyncSession,
    ) -> StepVersionResponse:
        """Merge user edits into the current Product Brief, creating a new version."""
        study = await self._get_study(study_id, db)

        if StudyStateMachine.is_step_locked(study, self.STEP):
            raise HTTPException(
                status_code=409,
                detail="Step 2 (Product Brief) is locked and cannot be edited.",
            )

        latest = await self._get_latest_version(study_id, self.STEP, db)
        if latest is None:
            raise HTTPException(
                status_code=404,
                detail="No existing Product Brief version. Generate an empty template first.",
            )

        updated_content = {**latest.content, **edits}
        next_version = await self._next_version(study_id, self.STEP, db)

        new_sv = StepVersion(
            id=uuid.uuid4(),
            study_id=study_id,
            step=self.STEP,
            version=next_version,
            status="review",
            content=updated_content,
            ai_rationale={"source": "manual_edit", "edits_applied": list(edits.keys())},
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_sv)

        if study.status == "step_2_draft":
            StudyStateMachine.transition(study, "step_2_review")

        await db.commit()
        await db.refresh(new_sv)

        await AuditService.log_event(
            study_id=study_id,
            action="product_brief_edited",
            actor="user",
            payload={"version": next_version, "edits": list(edits.keys())},
            db=db,
        )

        return StepVersionResponse.model_validate(new_sv)

    async def lock_product_brief(
        self,
        study_id: uuid.UUID,
        user_id: str,
        db: AsyncSession,
    ) -> StepVersionResponse:
        study = await self._get_study(study_id, db)

        if not StudyStateMachine.can_lock_step(study, self.STEP):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot lock Product Brief: study must be in 'step_2_review', "
                       f"currently '{study.status}'.",
            )

        latest = await self._get_latest_version(study_id, self.STEP, db)
        if latest is None:
            raise HTTPException(
                status_code=404,
                detail="No Product Brief version found to lock.",
            )

        # Validate required fields are non-empty before locking
        content = latest.content or {}
        required = ["product_name", "target_audience_description", "must_communicate"]
        missing = [f for f in required if not (content.get(f) or "").strip()]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot lock: required fields are empty — {', '.join(missing)}",
            )

        latest.status = "locked"
        latest.locked_at = datetime.now(timezone.utc)
        try:
            latest.locked_by = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        except ValueError:
            latest.locked_by = None

        StudyStateMachine.lock_step(study, self.STEP, user_id)

        await db.commit()
        await db.refresh(latest)

        await AuditService.log_event(
            study_id=study_id,
            action="product_brief_locked",
            actor=user_id,
            payload={"version": latest.version},
            db=db,
        )

        return StepVersionResponse.model_validate(latest)

    # ── Helpers ──

    @staticmethod
    async def _get_study(study_id, db):
        result = await db.execute(select(Study).where(Study.id == study_id))
        study = result.scalar_one_or_none()
        if not study:
            raise HTTPException(status_code=404, detail="Study not found")
        return study

    @staticmethod
    async def _get_locked_step(study_id, step, db):
        result = await db.execute(
            select(StepVersion).where(
                StepVersion.study_id == study_id,
                StepVersion.step == step,
                StepVersion.status == "locked",
            ).order_by(StepVersion.version.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _get_latest_version(study_id, step, db):
        result = await db.execute(
            select(StepVersion)
            .where(StepVersion.study_id == study_id, StepVersion.step == step)
            .order_by(StepVersion.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _next_version(study_id, step, db):
        result = await db.execute(
            select(sa_func.coalesce(sa_func.max(StepVersion.version), 0))
            .where(StepVersion.study_id == study_id, StepVersion.step == step)
        )
        return (result.scalar() or 0) + 1
