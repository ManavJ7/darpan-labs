"""Ad Creative Questionnaire (Step 4) service — generate questionnaire for ad creative testing.

Mirrors QuestionnaireService but uses ad-creative-specific sections (territory exposure,
unaided recall, aided branding, KPI modules M1-M6) and the ad_creative_questionnaire_generator prompt.
Edit, feedback, and lock logic are identical and delegated to the base questionnaire service.
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
from app.schemas.study import StepVersionResponse
from app.services.audit_service import AuditService
from app.services.state_machine import StudyStateMachine
from app.services.prompt_service import PromptService
from app.llm.client import LLMClient


# Metric → LINK+ module mapping. A metric_id selected by the user at Step 1
# implies the M-module it belongs to must be emitted by the questionnaire
# generator. This dict co-locates with the prompt it drives rather than
# living in the DB — if the prompt's module layout ever changes, both files
# change together.
METRIC_TO_MODULE: dict[str, str] = {
    # M1 — Distinctiveness
    "distinctive_impact": "M1_distinctiveness",
    "freshness": "M1_distinctiveness",
    "memorability": "M1_distinctiveness",
    "originality": "M1_distinctiveness",
    "stopping_power_m1": "M1_distinctiveness",
    # M2 — Message Clarity (communication_awareness is the only scorable
    # metric here; message_takeout / confusion_check / claim_recall are
    # free-text probes generated alongside when M2 is included).
    "communication_awareness": "M2_message_clarity",
    # M3 — Relevance & Resonance
    "relevance": "M3_relevance_resonance",
    "need_alignment": "M3_relevance_resonance",
    "enjoyment": "M3_relevance_resonance",
    "stopping_power": "M3_relevance_resonance",
    # M4 — Emotional Signature (Associations)
    "emotional_active_positive": "M4_emotional_signature",
    "emotional_active_negative": "M4_emotional_signature",
    "emotional_passive_positive": "M4_emotional_signature",
    "emotional_passive_negative": "M4_emotional_signature",
    # M5 — Brand Fit & Persuasion
    "brand_fit": "M5_brand_fit_persuasion",
    "persuasion_lift": "M5_brand_fit_persuasion",
    "affinity": "M5_brand_fit_persuasion",
    "advocacy": "M5_brand_fit_persuasion",
    "personality_match": "M5_brand_fit_persuasion",
}

ALL_MODULES: list[str] = [
    "M1_distinctiveness",
    "M2_message_clarity",
    "M3_relevance_resonance",
    "M4_emotional_signature",
    "M5_brand_fit_persuasion",
]


def derive_kpi_modules(recommended_metrics: list[str] | None) -> list[str]:
    """Project a list of user-picked metric_ids down to the unique set of
    LINK+ M-modules that cover them.

    Returns a sorted list (deterministic output for caching / audit). Falls
    back to every module if the user hasn't picked any recognised metrics —
    safer than emitting an empty questionnaire.
    """
    if not recommended_metrics:
        return list(ALL_MODULES)
    modules = {METRIC_TO_MODULE[m] for m in recommended_metrics if m in METRIC_TO_MODULE}
    if not modules:
        return list(ALL_MODULES)
    # sort by the canonical M1..M5 order
    return sorted(modules, key=lambda m: ALL_MODULES.index(m) if m in ALL_MODULES else 999)


def _normalize_questionnaire_options(questionnaire: dict) -> None:
    """Mutate questionnaire content in place: coerce scale.options from plain
    strings to {value, label} objects.

    The frontend expects each option as an object; the LLM sometimes returns
    bare strings (e.g. `["Under 20", "20-24"]`). This helper fixes that up so
    downstream rendering always works.
    """
    for section in questionnaire.get("sections", []) or []:
        for q in section.get("questions", []) or []:
            scale = q.get("scale") or {}
            opts = scale.get("options")
            if not isinstance(opts, list):
                continue
            normalized = []
            for i, opt in enumerate(opts):
                if isinstance(opt, dict):
                    # Already in good shape; fill missing keys defensively
                    normalized.append({
                        "value": opt.get("value", i + 1),
                        "label": str(opt.get("label", opt.get("value", ""))),
                    })
                elif isinstance(opt, str):
                    normalized.append({"value": i + 1, "label": opt})
                else:
                    normalized.append({"value": i + 1, "label": str(opt)})
            scale["options"] = normalized
            q["scale"] = scale


class AdCreativeQuestionnaireService:
    """Step 4 for ad_creative_testing studies."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        prompt_service: Optional[PromptService] = None,
    ):
        self.llm = llm_client or LLMClient()
        self.prompt_service = prompt_service or PromptService()

    async def generate_questionnaire(
        self,
        study_id: uuid.UUID,
        db: AsyncSession,
    ) -> StepVersionResponse:
        study = await self._get_study(study_id, db)

        if not StudyStateMachine.can_start_step(study, 5):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot start step 5 (Questionnaire): study status is '{study.status}'. "
                       f"Lock Step 4 (Research Design) first.",
            )

        # Load prerequisites — for ad_creative, steps are:
        # 1 = Study Brief, 2 = Product Brief, 3 = Territories, 4 = Research Design
        step1 = await self._get_locked_step(study_id, 1, db)  # Study Brief
        step2 = await self._get_locked_step(study_id, 2, db)  # Product Brief
        step4 = await self._get_locked_step(study_id, 4, db)  # Research Design

        # Load territories (concepts)
        concepts_result = await db.execute(
            select(Concept)
            .where(Concept.study_id == study_id)
            .order_by(Concept.concept_index)
        )
        concepts = concepts_result.scalars().all()

        brief_content = step1.content if step1 else {}
        product_brief_content = step2.content if step2 else {}
        design_content = step4.content if step4 else {}

        # Extract territory data for prompt
        territories = []
        for c in concepts:
            comp = c.components or {}
            territory = {"concept_index": c.concept_index}
            for field in ["territory_name", "core_insight", "big_idea", "key_message", "execution_sketch"]:
                val = comp.get(field, {})
                if isinstance(val, dict):
                    territory[field] = val.get("refined") or val.get("raw_input", "")
                else:
                    territory[field] = str(val)
            tm = comp.get("tone_mood", "")
            territory["tone_mood"] = tm if isinstance(tm, list) else ([tm] if tm else [])
            territory["target_emotion"] = comp.get("target_emotion", [])
            territories.append(territory)

        # Derive KPI modules from the user's picked metrics at Step 1.
        # The `recommended_metrics` list is the source of truth — it's what the
        # user checks in the wizard. The legacy `kpi_modules` field on the brief
        # was never populated, which is why the generator used to default to
        # emitting ALL modules regardless of selection.
        recommended_metrics = brief_content.get("recommended_metrics") or []
        kpi_modules = derive_kpi_modules(recommended_metrics)

        prompt = self.prompt_service.format_prompt(
            "ad_creative_questionnaire_generator",
            brand_name=study.brand_name or "Unknown",
            category=study.category or "General",
            campaign_objective=brief_content.get("campaign_objective", "brand_building"),
            num_territories=str(len(territories)),
            methodology=design_content.get("testing_methodology", "sequential_monadic"),
            territories_per_respondent=str(design_content.get("concepts_per_respondent", len(territories))),
            study_id=str(study_id),
            study_brief_json=json.dumps(brief_content, indent=2),
            product_brief_json=json.dumps(product_brief_content, indent=2),
            territories_json=json.dumps(territories, indent=2),
            research_design_json=json.dumps(design_content, indent=2),
            selected_kpi_modules=", ".join(kpi_modules),
        )

        try:
            questionnaire_content = await self.llm.generate_json(prompt, max_tokens=32000)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"LLM generation failed: {e}")

        # Normalize scale options: the LLM occasionally returns plain strings
        # instead of {value, label} objects. Coerce to the canonical shape.
        _normalize_questionnaire_options(questionnaire_content)

        # Transition status: step_4_locked → step_5_draft → step_5_review
        if study.status == "step_4_locked":
            StudyStateMachine.transition(study, "step_5_draft")
        if study.status == "step_5_draft":
            StudyStateMachine.transition(study, "step_5_review")

        next_version = await self._next_version(study_id, 5, db)
        step_version = StepVersion(
            id=uuid.uuid4(),
            study_id=study_id,
            step=5,
            version=next_version,
            status="review",
            content=questionnaire_content,
            ai_rationale={"source": "llm_generated", "model": self.llm.model, "kpi_modules": kpi_modules},
            created_at=datetime.now(timezone.utc),
        )
        db.add(step_version)
        await db.commit()
        await db.refresh(step_version)

        await AuditService.log_event(
            study_id=study_id,
            action="step_4_generated",
            actor="system",
            payload={"version": next_version, "study_type": "ad_creative_testing"},
            db=db,
        )

        return StepVersionResponse.model_validate(step_version)

    # Edit, feedback, and lock delegate to the base questionnaire service
    # (same logic — CRUD on questions, section feedback, locking)

    async def edit_questionnaire(self, study_id, operations, db):
        from app.services.questionnaire_service import QuestionnaireService
        svc = QuestionnaireService(llm_client=self.llm, prompt_service=self.prompt_service, step_number=5)
        return await svc.edit_questionnaire(study_id, operations, db)

    async def submit_section_feedback(self, study_id, section_id, feedback, db):
        from app.services.questionnaire_service import QuestionnaireService
        svc = QuestionnaireService(llm_client=self.llm, prompt_service=self.prompt_service, step_number=5)
        return await svc.submit_section_feedback(study_id, section_id, feedback, db)

    async def lock_questionnaire(self, study_id, user_id, db):
        from app.services.questionnaire_service import QuestionnaireService
        svc = QuestionnaireService(llm_client=self.llm, prompt_service=self.prompt_service, step_number=5)
        return await svc.lock_questionnaire(study_id, user_id, db)

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
    async def _next_version(study_id, step, db):
        result = await db.execute(
            select(sa_func.coalesce(sa_func.max(StepVersion.version), 0))
            .where(StepVersion.study_id == study_id, StepVersion.step == step)
        )
        return (result.scalar() or 0) + 1
