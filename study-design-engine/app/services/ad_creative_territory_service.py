"""Ad Creative Territory (Step 2) service — generate, refine, approve territories.

Mirrors ConceptBoardService but uses the 7-field creative territory structure
and the ad_creative_territory_refiner prompt. Reuses the Concept model
(JSONB components field stores territory data).
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.study import Study, StepVersion
from app.models.concept import Concept
from app.schemas.ad_creative import TONE_MOOD_OPTIONS, TARGET_EMOTION_OPTIONS
from app.services.audit_service import AuditService
from app.services.state_machine import StudyStateMachine
from app.services.prompt_service import PromptService
from app.llm.client import LLMClient


# Default empty territory template
def _empty_territory(index: int) -> dict:
    return {
        "territory_name": {"raw_input": "", "refined": None, "approved": False},
        "core_insight": {"raw_input": "", "refined": None, "approved": False},
        "big_idea": {"raw_input": "", "refined": None, "approved": False},
        "key_message": {"raw_input": "", "refined": None, "approved": False},
        "tone_mood": "",
        "execution_sketch": {"raw_input": "", "refined": None, "approved": False},
        "target_emotion": [],
    }


class AdCreativeTerritoryService:
    """Step 2 for ad_creative_testing studies."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        prompt_service: Optional[PromptService] = None,
    ):
        self.llm = llm_client or LLMClient()
        self.prompt_service = prompt_service or PromptService()

    async def generate_territories(
        self,
        study_id: uuid.UUID,
        num_territories: int,
        db: AsyncSession,
    ) -> list[dict]:
        """Create N empty territory templates (Step 3 of ad_creative_testing)."""
        study = await self._get_study(study_id, db)

        if not StudyStateMachine.can_start_step(study, 3):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot start step 3 (Territories): study status is '{study.status}'. "
                       f"Lock Step 2 (Product Brief) first.",
            )

        # Transition to step_3_draft
        if study.status == "step_2_locked":
            StudyStateMachine.transition(study, "step_3_draft")

        territories = []
        for i in range(num_territories):
            concept = Concept(
                study_id=study_id,
                concept_index=i + 1,  # 1-indexed
                version=1,
                status="raw",
                components=_empty_territory(i + 1),
            )
            db.add(concept)
            await db.flush()
            territories.append({
                "id": str(concept.id),
                "study_id": str(study_id),
                "concept_index": concept.concept_index,
                "version": concept.version,
                "status": concept.status,
                "components": concept.components,
                "created_at": concept.created_at.isoformat() if concept.created_at else None,
            })

        await db.commit()

        await AuditService.log_event(
            study_id=study_id,
            action="territories_generated",
            actor="system",
            payload={"count": num_territories},
            db=db,
        )

        return territories

    async def add_territory(
        self,
        study_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict:
        """Add a single empty territory to an existing ad_creative study.

        Pre-conditions:
        - Study must be in step_2_locked (first territory), step_3_draft, or step_3_review.
        """
        study = await self._get_study(study_id, db)

        if study.status == "step_2_locked":
            StudyStateMachine.transition(study, "step_3_draft")
        elif study.status not in ("step_3_draft", "step_3_review"):
            raise ValueError(
                f"Cannot add territory: study must be in step_2_locked, step_3_draft, or step_3_review, "
                f"currently '{study.status}'"
            )

        # Find next concept_index
        result = await db.execute(
            select(Concept).where(Concept.study_id == study_id).order_by(Concept.concept_index.desc())
        )
        last = result.scalars().first()
        next_index = (last.concept_index + 1) if last else 1

        concept = Concept(
            study_id=study_id,
            concept_index=next_index,
            version=1,
            status="raw",
            components=_empty_territory(next_index),
            comparability_flags=[],
        )
        db.add(concept)
        await db.commit()
        await db.refresh(concept)

        return {
            "id": str(concept.id),
            "study_id": str(concept.study_id),
            "concept_index": concept.concept_index,
            "version": concept.version,
            "status": concept.status,
            "components": concept.components,
            "comparability_flags": concept.comparability_flags,
            "image_url": concept.image_url,
            "created_at": concept.created_at,
        }

    async def delete_territory(
        self,
        study_id: uuid.UUID,
        territory_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict:
        """Delete a territory from an ad_creative study.

        Pre-conditions:
        - Step 3 must not be locked.
        """
        study = await self._get_study(study_id, db)

        if StudyStateMachine.is_step_locked(study, 3):
            raise ValueError("Cannot delete territory: step 3 is locked.")

        concept = await self._get_concept(territory_id, db)
        await db.delete(concept)
        await db.commit()

        return {"deleted": True, "territory_id": str(territory_id)}

    async def refine_territory(
        self,
        study_id: uuid.UUID,
        territory_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict:
        """Run the two-pass LLM refinement on a territory."""
        study = await self._get_study(study_id, db)
        concept = await self._get_concept(territory_id, db)

        components = concept.components or {}

        def _get_text(field: str) -> str:
            val = components.get(field, {})
            if isinstance(val, dict):
                return val.get("raw_input", "")
            return str(val)

        # Load Product Brief (step 2) for grounding the refinement
        product_brief_version = await db.execute(
            select(StepVersion).where(
                StepVersion.study_id == study_id,
                StepVersion.step == 2,
                StepVersion.status == "locked",
            ).order_by(StepVersion.version.desc()).limit(1)
        )
        pb = product_brief_version.scalar_one_or_none()
        product_brief_content = pb.content if pb else {}

        # Get other territories for distinctiveness check
        all_concepts = await db.execute(
            select(Concept).where(
                Concept.study_id == study_id,
                Concept.id != territory_id,
            )
        )
        others = all_concepts.scalars().all()
        other_summaries = []
        for o in others:
            oc = o.components or {}
            name = oc.get("territory_name", {})
            name_text = name.get("raw_input", "") if isinstance(name, dict) else str(name)
            idea = oc.get("big_idea", {})
            idea_text = idea.get("raw_input", "") if isinstance(idea, dict) else str(idea)
            other_summaries.append(f"- {name_text}: {idea_text[:100]}")

        prompt = self.prompt_service.format_prompt(
            "ad_creative_territory_refiner",
            territory_name=_get_text("territory_name"),
            core_insight=_get_text("core_insight"),
            big_idea=_get_text("big_idea"),
            key_message=_get_text("key_message"),
            tone_mood=", ".join(components.get("tone_mood", []))
                if isinstance(components.get("tone_mood"), list)
                else (components.get("tone_mood", "") or ""),
            execution_sketch=_get_text("execution_sketch"),
            target_emotion=", ".join(components.get("target_emotion", [])),
            brand_name=study.brand_name or "Unknown",
            category=study.category or "General",
            product_brief_json=json.dumps(product_brief_content, indent=2),
            other_territories_summary="\n".join(other_summaries) if other_summaries else "None",
        )

        try:
            result = await self.llm.generate_json(prompt)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"LLM refinement failed: {e}")

        # Merge refined components back into the territory
        from sqlalchemy.orm.attributes import flag_modified
        refined = result.get("refined_components", {})
        for field_name, field_data in refined.items():
            if field_name in components and isinstance(components[field_name], dict):
                if isinstance(field_data, dict) and "refined" in field_data:
                    components[field_name]["refined"] = field_data["refined"]
                    components[field_name]["refinement_rationale"] = field_data.get("refinement_rationale", "")

        concept.components = components
        flag_modified(concept, "components")
        concept.status = "refined"
        concept.comparability_flags = result.get("flags", [])
        flag_modified(concept, "comparability_flags")

        await db.commit()
        await db.refresh(concept)

        # Response must match ConceptRefineResponse schema:
        #   concept_id: UUID, refined_components: dict, flags: list[str], testability_score: float
        return {
            "concept_id": str(concept.id),
            "refined_components": refined,
            "flags": result.get("flags", []),
            "testability_score": result.get("testability_score", 0.0),
        }

    async def update_territory(
        self,
        study_id: uuid.UUID,
        territory_id: uuid.UUID,
        components: dict,
        db: AsyncSession,
    ) -> dict:
        """Update territory components (user edits)."""
        concept = await self._get_concept(territory_id, db)
        # Force SQLAlchemy to treat the JSONB column as modified
        # (in-place mutation of a dict field isn't auto-detected)
        from sqlalchemy.orm.attributes import flag_modified
        concept.components = {**(concept.components or {}), **components}
        flag_modified(concept, "components")
        await db.commit()
        await db.refresh(concept)
        return {
            "id": str(concept.id),
            "study_id": str(concept.study_id),
            "concept_index": concept.concept_index,
            "version": concept.version,
            "status": concept.status,
            "components": concept.components,
            "comparability_flags": concept.comparability_flags,
            "image_url": concept.image_url,
            "created_at": concept.created_at,
            "updated_at": getattr(concept, "updated_at", None),
        }

    async def approve_territory(
        self,
        study_id: uuid.UUID,
        territory_id: uuid.UUID,
        approved: dict,
        db: AsyncSession,
    ) -> dict:
        """Approve refined fields. Same pattern as concept approval."""
        from sqlalchemy.orm.attributes import flag_modified
        concept = await self._get_concept(territory_id, db)
        components = concept.components or {}

        for field_name, is_approved in approved.items():
            if field_name in components and isinstance(components[field_name], dict):
                components[field_name]["approved"] = bool(is_approved)

        concept.components = components
        flag_modified(concept, "components")
        concept.status = "approved"
        await db.commit()
        await db.refresh(concept)
        return {
            "id": str(concept.id),
            "study_id": str(concept.study_id),
            "concept_index": concept.concept_index,
            "version": concept.version,
            "status": concept.status,
            "components": concept.components,
            "comparability_flags": concept.comparability_flags,
            "image_url": concept.image_url,
            "created_at": concept.created_at,
            "updated_at": getattr(concept, "updated_at", None),
        }

    async def lock_territories(
        self,
        study_id: uuid.UUID,
        user_id: str,
        db: AsyncSession,
    ) -> dict:
        """Lock Step 3 (Territories) for ad_creative_testing studies.

        Mirrors ConceptBoardService.lock_concepts but operates on step=3.
        All territories must be in 'approved' status.
        """
        study = await self._get_study(study_id, db)

        # If still in step_3_draft, transition to step_3_review first
        if study.status == "step_3_draft":
            StudyStateMachine.transition(study, "step_3_review")

        result = await db.execute(
            select(Concept).where(Concept.study_id == study_id).order_by(Concept.concept_index)
        )
        concepts = list(result.scalars().all())

        if not concepts:
            raise ValueError(f"No territories found for study {study_id}")

        unapproved = [c.concept_index for c in concepts if c.status != "approved"]
        if unapproved:
            raise ValueError(
                f"Cannot lock step 3: territories at indices {unapproved} are not approved"
            )

        # Lock via state machine
        StudyStateMachine.lock_step(study, 3, user_id)

        # Snapshot into StepVersion with step=3
        step_content = {
            "concepts": [
                {
                    "concept_id": str(c.id),
                    "concept_index": c.concept_index,
                    "version": c.version,
                    "status": c.status,
                    "components": c.components,
                }
                for c in concepts
            ]
        }

        existing = await db.execute(
            select(StepVersion).where(
                StepVersion.study_id == study_id, StepVersion.step == 3
            )
        )
        next_version = max((sv.version for sv in existing.scalars().all()), default=0) + 1

        try:
            locked_by_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        except ValueError:
            locked_by_uuid = None

        step_version = StepVersion(
            study_id=study_id,
            step=3,
            version=next_version,
            status="locked",
            content=step_content,
            locked_at=datetime.now(timezone.utc),
            locked_by=locked_by_uuid,
        )
        db.add(step_version)
        await db.commit()
        await db.refresh(step_version)

        return {
            "study_id": str(study_id),
            "step": 3,
            "version": step_version.version,
            "status": "locked",
            "locked_at": step_version.locked_at.isoformat() if step_version.locked_at else None,
            "locked_by": user_id,
            "num_territories": len(concepts),
        }

    # ── Helpers ──

    @staticmethod
    async def _get_study(study_id, db):
        result = await db.execute(select(Study).where(Study.id == study_id))
        study = result.scalar_one_or_none()
        if not study:
            raise HTTPException(status_code=404, detail="Study not found")
        return study

    @staticmethod
    async def _get_concept(concept_id, db):
        result = await db.execute(select(Concept).where(Concept.id == concept_id))
        concept = result.scalar_one_or_none()
        if not concept:
            raise HTTPException(status_code=404, detail="Territory not found")
        return concept
