"""Research Design Service — Step 3 generation, editing, and locking."""

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.client import LLMClient, get_llm_client
from app.models.concept import Concept
from app.models.study import StepVersion, Study
from app.schemas.research_design import ResearchDesignContent
from app.schemas.study import StepVersionResponse
from app.services.prompt_service import PromptService, get_prompt_service
from app.services.sample_calculator import SampleCalculator
from app.services.state_machine import StudyStateMachine

logger = logging.getLogger(__name__)


class ResearchDesignService:
    """Orchestrates Step 3 — Research Design Document.

    - generate_design: validates prerequisites, loads context from earlier steps,
      calls the LLM for qualitative recommendations, then uses SampleCalculator
      for all deterministic computations.
    - edit_design: applies user edits and recalculates affected fields.
    - lock_design: transitions the study to step_3_locked.
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        prompt_service: PromptService | None = None,
    ):
        self.llm = llm_client or get_llm_client()
        self.prompts = prompt_service or get_prompt_service()

    # ── Generate Design ──────────────────────────────────────────

    async def generate_design(
        self,
        study_id: uuid.UUID,
        db: AsyncSession,
    ) -> StepVersionResponse:
        """Generate Step 3 research design for the given study.

        Prerequisites:
        1. Study must exist.
        2. Step 2 must be locked (study.status == 'step_2_locked').
        3. Load step 1 content (study brief) and step 2 concepts.
        4. Call LLM for recommendations (methodology, rotation, language, etc.).
        5. Use SampleCalculator for sample size, quotas, duration, cost.
        6. Persist as a new StepVersion and transition study to step_3_draft.
        """
        # 1. Load study
        study = await self._get_study(study_id, db)

        # 2. Validate prerequisite: step 2 locked
        if not StudyStateMachine.can_start_step(study, 3):
            raise ValueError(
                f"Cannot generate Step 3: study must be in step_2_locked status, "
                f"currently '{study.status}'"
            )

        # 3. Load step 1 (study brief) and step 2 (concepts)
        brief_content = await self._load_step_content(study_id, step=1, db=db)
        concepts_content = await self._load_concepts(study_id, db)

        # Extract selected metrics from the brief
        selected_metrics = brief_content.get("recommended_metrics", [])

        # 4. Call LLM for qualitative recommendations
        prompt = self.prompts.format_prompt(
            "research_design_generator",
            study_brief_json=json.dumps(brief_content, default=str),
            concepts_json=json.dumps(concepts_content, default=str),
            selected_metrics_json=json.dumps(selected_metrics, default=str),
        )
        llm_recommendations = await self.llm.generate_json(prompt)

        # 5. Extract LLM-recommended parameters
        methodology = llm_recommendations.get(
            "testing_methodology",
            brief_content.get("methodology_family", "sequential_monadic"),
        )
        concepts_per_respondent = llm_recommendations.get("concepts_per_respondent", 3)
        data_collection_method = llm_recommendations.get(
            "data_collection_method", "online_panel"
        )
        rotation_design = llm_recommendations.get(
            "rotation_design", "balanced_incomplete_block"
        )
        survey_language = llm_recommendations.get("survey_language", ["english"])
        confidence_level = llm_recommendations.get("confidence_level", 0.95)
        margin_of_error = llm_recommendations.get("margin_of_error", 0.05)

        num_concepts = len(concepts_content) if concepts_content else 1
        demographic_dims = llm_recommendations.get("demographic_quotas", [])

        # 6. Deterministic calculations via SampleCalculator
        sample_result = SampleCalculator.calculate_sample_size(
            methodology=methodology,
            num_concepts=num_concepts,
            concepts_per_respondent=concepts_per_respondent,
            confidence_level=confidence_level,
            margin_of_error=margin_of_error,
        )

        quotas: list[dict] = []
        if demographic_dims:
            quota_allocs = SampleCalculator.allocate_quotas(
                sample_result.total_respondents, demographic_dims
            )
            quotas = [q.model_dump() for q in quota_allocs]

        # 7. Build content payload
        content = ResearchDesignContent(
            testing_methodology=methodology,
            concepts_per_respondent=concepts_per_respondent,
            total_sample_size=sample_result.total_respondents,
            confidence_level=confidence_level,
            margin_of_error=margin_of_error,
            demographic_quotas=quotas,
            rotation_design=rotation_design,
            data_collection_method=data_collection_method,
            survey_language=survey_language,
        )

        ai_rationale = {
            "llm_recommendations": llm_recommendations,
            "sample_size_details": sample_result.model_dump(),
        }

        # 8. Determine version number
        version = await self._next_version(study_id, step=3, db=db)

        # 9. Persist StepVersion
        step_version = StepVersion(
            study_id=study_id,
            step=3,
            version=version,
            status="draft",
            content=content.model_dump(),
            ai_rationale=ai_rationale,
        )
        db.add(step_version)

        # 10. Transition study status (draft → review, like study_brief_service)
        StudyStateMachine.transition(study, "step_3_draft")
        StudyStateMachine.transition(study, "step_3_review")
        step_version.status = "review"
        await db.commit()
        await db.refresh(step_version)

        return StepVersionResponse(
            id=step_version.id,
            study_id=step_version.study_id,
            step=step_version.step,
            version=step_version.version,
            status=step_version.status,
            content=step_version.content,
            ai_rationale=step_version.ai_rationale,
            locked_at=step_version.locked_at,
            created_at=step_version.created_at,
        )

    # ── Edit Design ──────────────────────────────────────────────

    async def edit_design(
        self,
        study_id: uuid.UUID,
        edits: dict,
        db: AsyncSession,
    ) -> StepVersionResponse:
        """Apply user edits to the current Step 3 draft and recalculate.

        The study must be in step_3_draft or step_3_review status.
        Creates a new version with the updated content.
        """
        study = await self._get_study(study_id, db)

        if not StudyStateMachine.can_edit_step(study, 3):
            raise ValueError(
                f"Cannot edit Step 3: step is locked. Study status: '{study.status}'"
            )

        # Ensure study is at step 3
        current_step = StudyStateMachine.get_current_step(study)
        if current_step != 3:
            raise ValueError(
                f"Cannot edit Step 3: study is currently at step {current_step}"
            )

        # Load latest step 3 version
        latest = await self._load_latest_step_version(study_id, step=3, db=db)
        if latest is None:
            raise ValueError("No existing Step 3 design to edit. Generate one first.")

        current_content = dict(latest.content)

        # Inject num_concepts for recalculate_on_edit if not present
        concepts = await self._load_concepts(study_id, db)
        if "num_concepts" not in current_content:
            current_content["num_concepts"] = len(concepts) if concepts else 1

        # Recalculate
        updated_content = SampleCalculator.recalculate_on_edit(current_content, edits)

        # Remove helper keys not part of the schema
        updated_content.pop("num_concepts", None)
        updated_content.pop("methodology", None)
        updated_content.pop("min_per_subgroup", None)
        updated_content.pop("num_subgroups", None)

        # New version
        new_version = latest.version + 1
        step_version = StepVersion(
            study_id=study_id,
            step=3,
            version=new_version,
            status="draft",
            content=updated_content,
            ai_rationale=latest.ai_rationale,
        )
        db.add(step_version)

        # If study was in review, move back to draft
        if study.status == "step_3_review":
            StudyStateMachine.transition(study, "step_3_draft")

        await db.commit()
        await db.refresh(step_version)

        return StepVersionResponse(
            id=step_version.id,
            study_id=step_version.study_id,
            step=step_version.step,
            version=step_version.version,
            status=step_version.status,
            content=step_version.content,
            ai_rationale=step_version.ai_rationale,
            locked_at=step_version.locked_at,
            created_at=step_version.created_at,
        )

    # ── Lock Design ──────────────────────────────────────────────

    async def lock_design(
        self,
        study_id: uuid.UUID,
        user_id: str,
        db: AsyncSession,
    ) -> StepVersionResponse:
        """Lock Step 3 — freeze the research design.

        Study must be in step_3_review.
        """
        study = await self._get_study(study_id, db)

        if not StudyStateMachine.can_lock_step(study, 3):
            raise ValueError(
                f"Cannot lock Step 3: study must be in step_3_review status, "
                f"currently '{study.status}'"
            )

        latest = await self._load_latest_step_version(study_id, step=3, db=db)
        if latest is None:
            raise ValueError("No Step 3 design exists to lock.")

        # Update the step version
        latest.status = "locked"
        latest.locked_at = datetime.now(timezone.utc)
        try:
            latest.locked_by = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        except ValueError:
            latest.locked_by = None

        # Transition study
        StudyStateMachine.lock_step(study, 3, user_id)

        await db.commit()
        await db.refresh(latest)

        return StepVersionResponse(
            id=latest.id,
            study_id=latest.study_id,
            step=latest.step,
            version=latest.version,
            status=latest.status,
            content=latest.content,
            ai_rationale=latest.ai_rationale,
            locked_at=latest.locked_at,
            created_at=latest.created_at,
        )

    # ── Private Helpers ──────────────────────────────────────────

    async def _get_study(self, study_id: uuid.UUID, db: AsyncSession) -> Study:
        result = await db.execute(select(Study).where(Study.id == study_id))
        study = result.scalar_one_or_none()
        if study is None:
            raise ValueError(f"Study {study_id} not found")
        return study

    async def _load_step_content(
        self, study_id: uuid.UUID, step: int, db: AsyncSession
    ) -> dict:
        result = await db.execute(
            select(StepVersion)
            .where(StepVersion.study_id == study_id, StepVersion.step == step)
            .order_by(StepVersion.version.desc())
            .limit(1)
        )
        sv = result.scalar_one_or_none()
        if sv is None:
            raise ValueError(f"Step {step} content not found for study {study_id}")
        return sv.content

    async def _load_concepts(
        self, study_id: uuid.UUID, db: AsyncSession
    ) -> list[dict]:
        result = await db.execute(
            select(Concept).where(Concept.study_id == study_id)
        )
        concepts = result.scalars().all()
        return [
            {
                "concept_index": c.concept_index,
                "version": c.version,
                "status": c.status,
                "components": c.components,
            }
            for c in concepts
        ]

    async def _load_latest_step_version(
        self, study_id: uuid.UUID, step: int, db: AsyncSession
    ) -> StepVersion | None:
        result = await db.execute(
            select(StepVersion)
            .where(StepVersion.study_id == study_id, StepVersion.step == step)
            .order_by(StepVersion.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _next_version(
        self, study_id: uuid.UUID, step: int, db: AsyncSession
    ) -> int:
        latest = await self._load_latest_step_version(study_id, step, db)
        return (latest.version + 1) if latest else 1
