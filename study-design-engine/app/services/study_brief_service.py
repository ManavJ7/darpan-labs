"""Study Brief (Step 1) service — generate, edit, and lock the study brief."""

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


class StudyBriefService:
    """Orchestrates Step 1 (Study Brief) generation, editing, and locking."""

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
        """Generate the Step 1 study brief using LLM.

        Workflow:
        1. Load the study and validate its status allows step 1 generation.
        2. Load the metric library as JSON for the prompt context.
        3. Build the prompt from the study_brief_generator template.
        4. Call the LLM to produce a structured study brief.
        5. Persist a new StepVersion record (step=1, version auto-incremented).
        6. Transition study status to step_1_review.
        7. Log the action to the audit trail.

        Args:
            study_id: UUID of the study.
            db: Async database session.

        Raises:
            HTTPException 404 if study not found.
            HTTPException 409 if study status does not allow generation.
            HTTPException 502 if LLM call fails.

        Returns:
            StepVersionResponse for the newly created version.
        """
        # 1. Load study
        study = await self._get_study(study_id, db)

        # Validate status allows generation (init or step_1_draft)
        if study.status not in ("init", "step_1_draft"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot generate brief: study is in '{study.status}' status. "
                       f"Must be in 'init' or 'step_1_draft'.",
            )

        # 2. Load metric library
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
        metric_library_json = json.dumps(metric_dicts, indent=2)

        # 3. Build prompt
        brand_context = study.context or {}
        # Collect all context into a readable string for the LLM
        context_parts = []
        for key, val in brand_context.items():
            if key in ("revenue_range", "previous_studies"):
                continue  # handled separately
            context_parts.append(f"- {key}: {val}")
        additional_context = "\n".join(context_parts) if context_parts else "None provided"

        prompt = self.prompt_service.format_prompt(
            "study_brief_generator",
            metric_library_json=metric_library_json,
            brand_name=study.brand_name or "Unknown",
            category=study.category or "General",
            revenue_range=brand_context.get("revenue_range", "Not specified"),
            previous_studies=json.dumps(brand_context.get("previous_studies", [])),
            additional_context=additional_context,
            brand_question=study.question,
        )

        # 4. Call LLM
        try:
            brief_content = await self.llm.generate_json(prompt)
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"LLM generation failed: {str(e)}",
            )

        # 5. Determine next version number
        next_version = await self._next_version(study_id, step=1, db=db)

        now = datetime.now(timezone.utc)
        step_version = StepVersion(
            id=uuid.uuid4(),
            study_id=study_id,
            step=1,
            version=next_version,
            status="review",
            content=brief_content,
            ai_rationale={"source": "llm_generated", "model": self.llm.model},
            created_at=now,
        )
        db.add(step_version)

        # 6. Transition study status
        if study.status == "init":
            StudyStateMachine.transition(study, "step_1_draft")
        # Then move to review
        if study.status == "step_1_draft":
            StudyStateMachine.transition(study, "step_1_review")

        await db.commit()
        await db.refresh(step_version)

        # 7. Audit
        await AuditService.log_event(
            study_id=study_id,
            action="step_1_generated",
            actor="system",
            payload={"version": next_version},
            db=db,
        )

        return StepVersionResponse.model_validate(step_version)

    async def edit_brief(
        self,
        study_id: uuid.UUID,
        edits: dict,
        db: AsyncSession,
    ) -> StepVersionResponse:
        """Apply manual edits to the latest Step 1 version, creating a new version.

        Args:
            study_id: UUID of the study.
            edits: Dict of field-level overrides to merge into the brief content.
            db: Async database session.

        Raises:
            HTTPException 404 if study or step version not found.
            HTTPException 409 if step 1 is locked.

        Returns:
            StepVersionResponse for the new version.
        """
        study = await self._get_study(study_id, db)

        # Check step is not locked
        if StudyStateMachine.is_step_locked(study, 1):
            raise HTTPException(
                status_code=409,
                detail="Step 1 is locked and cannot be edited.",
            )

        # Get latest step 1 version
        latest = await self._get_latest_version(study_id, step=1, db=db)
        if latest is None:
            raise HTTPException(
                status_code=404,
                detail="No existing Step 1 version found. Generate a brief first.",
            )

        # Merge edits into content
        updated_content = {**latest.content, **edits}
        next_version = await self._next_version(study_id, step=1, db=db)

        now = datetime.now(timezone.utc)
        new_sv = StepVersion(
            id=uuid.uuid4(),
            study_id=study_id,
            step=1,
            version=next_version,
            status="review",
            content=updated_content,
            ai_rationale={"source": "manual_edit", "edits_applied": list(edits.keys())},
            created_at=now,
        )
        db.add(new_sv)

        # Transition to step_1_review if in step_1_draft
        if study.status == "step_1_draft":
            StudyStateMachine.transition(study, "step_1_review")

        await db.commit()
        await db.refresh(new_sv)

        # Audit
        await AuditService.log_event(
            study_id=study_id,
            action="step_1_edited",
            actor="user",
            payload={"version": next_version, "edits": list(edits.keys())},
            db=db,
        )

        return StepVersionResponse.model_validate(new_sv)

    async def lock_brief(
        self,
        study_id: uuid.UUID,
        user_id: str,
        db: AsyncSession,
    ) -> StepVersionResponse:
        """Lock Step 1, preventing further edits.

        Args:
            study_id: UUID of the study.
            user_id: ID of the user performing the lock.
            db: Async database session.

        Raises:
            HTTPException 404 if study or version not found.
            HTTPException 409 if study is not in step_1_review status.

        Returns:
            StepVersionResponse for the locked version.
        """
        study = await self._get_study(study_id, db)

        # Validate that step 1 can be locked
        if not StudyStateMachine.can_lock_step(study, 1):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot lock step 1: study must be in 'step_1_review' status, "
                       f"currently in '{study.status}'.",
            )

        # Get latest version
        latest = await self._get_latest_version(study_id, step=1, db=db)
        if latest is None:
            raise HTTPException(
                status_code=404,
                detail="No Step 1 version found to lock.",
            )

        # Lock the version
        latest.status = "locked"
        latest.locked_at = datetime.now(timezone.utc)
        try:
            latest.locked_by = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        except ValueError:
            latest.locked_by = None

        # Transition study to step_1_locked
        StudyStateMachine.lock_step(study, 1, user_id)

        await db.commit()
        await db.refresh(latest)

        # Audit
        await AuditService.log_event(
            study_id=study_id,
            action="step_1_locked",
            actor=user_id,
            payload={"version": latest.version},
            db=db,
        )

        return StepVersionResponse.model_validate(latest)

    # ------------------------------------------------------------------ helpers

    @staticmethod
    async def _get_study(study_id: uuid.UUID, db: AsyncSession) -> Study:
        """Fetch a study or raise 404."""
        result = await db.execute(select(Study).where(Study.id == study_id))
        study = result.scalar_one_or_none()
        if study is None:
            raise HTTPException(status_code=404, detail="Study not found")
        return study

    @staticmethod
    async def _get_latest_version(
        study_id: uuid.UUID,
        step: int,
        db: AsyncSession,
    ) -> Optional[StepVersion]:
        """Return the latest StepVersion for a given study and step."""
        result = await db.execute(
            select(StepVersion)
            .where(StepVersion.study_id == study_id, StepVersion.step == step)
            .order_by(StepVersion.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _next_version(
        study_id: uuid.UUID,
        step: int,
        db: AsyncSession,
    ) -> int:
        """Calculate the next version number for a step."""
        result = await db.execute(
            select(sa_func.coalesce(sa_func.max(StepVersion.version), 0))
            .where(StepVersion.study_id == study_id, StepVersion.step == step)
        )
        current_max = result.scalar()
        return (current_max or 0) + 1
