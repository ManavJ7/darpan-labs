"""Questionnaire Builder service — Step 4 of the Study Design Engine."""

import json
import math
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.client import LLMClient, get_llm_client
from app.models.study import Study, StepVersion
from app.schemas.questionnaire import (
    QuestionnaireContent,
    QuestionnaireSection,
    SectionFeedbackRequest,
    SectionFeedbackResponse,
)
from app.schemas.study import StepVersionResponse
from app.services.prompt_service import PromptService, get_prompt_service
from app.services.state_machine import StudyStateMachine


# Duration constants (seconds per question type)
DURATION_SECONDS = {
    "single_select": 15,
    "multi_select": 20,
    "open_text": 60,
    "rating": 15,
    "ranking": 30,
    "concept_exposure": 30,
}
DURATION_BUFFER_SECONDS = 60


class QuestionnaireService:
    """Handles questionnaire generation, feedback, locking, and validation for Step 4."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        prompt_service: PromptService | None = None,
    ):
        self.llm = llm_client or get_llm_client()
        self.prompts = prompt_service or get_prompt_service()

    # ── helpers ───────────────────────────────────────────────────────────

    async def _load_study(self, study_id: uuid.UUID, db: AsyncSession) -> Study:
        """Fetch a study by ID or raise ValueError."""
        result = await db.execute(select(Study).where(Study.id == study_id))
        study = result.scalar_one_or_none()
        if study is None:
            raise ValueError(f"Study {study_id} not found")
        return study

    async def _load_step_version(
        self, study_id: uuid.UUID, step: int, db: AsyncSession
    ) -> StepVersion | None:
        """Return the latest version for a given step, or None."""
        result = await db.execute(
            select(StepVersion)
            .where(StepVersion.study_id == study_id, StepVersion.step == step)
            .order_by(desc(StepVersion.version))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _load_all_previous_outputs(
        self, study_id: uuid.UUID, db: AsyncSession
    ) -> dict:
        """Load the latest content for steps 1-3."""
        outputs: dict = {}
        for step_num in (1, 2, 3):
            sv = await self._load_step_version(study_id, step_num, db)
            if sv is not None:
                outputs[f"step_{step_num}"] = sv.content
            else:
                outputs[f"step_{step_num}"] = {}
        return outputs

    def _step_version_to_response(self, sv: StepVersion) -> StepVersionResponse:
        """Convert a StepVersion ORM object to a StepVersionResponse schema."""
        return StepVersionResponse(
            id=sv.id,
            study_id=sv.study_id,
            step=sv.step,
            version=sv.version,
            status=sv.status,
            content=sv.content,
            ai_rationale=sv.ai_rationale,
            locked_at=sv.locked_at,
            created_at=sv.created_at,
        )

    # ── generate_questionnaire ───────────────────────────────────────────

    async def generate_questionnaire(
        self, study_id: uuid.UUID, db: AsyncSession
    ) -> StepVersionResponse:
        """Generate a questionnaire (step 4) from all prior step outputs.

        Pre-conditions:
        - Step 3 must be locked.
        """
        study = await self._load_study(study_id, db)

        # Validate that step 3 is locked (prerequisite for step 4)
        if not StudyStateMachine.can_start_step(study, 4):
            raise ValueError(
                f"Cannot generate questionnaire: step 3 must be locked. "
                f"Current study status is '{study.status}'"
            )

        # Load all previous outputs
        prev = await self._load_all_previous_outputs(study_id, db)

        # Build the prompt
        prompt = self.prompts.format_prompt(
            "questionnaire_generator",
            study_brief_json=json.dumps(prev.get("step_1", {}), indent=2),
            concepts_json=json.dumps(prev.get("step_2", {}), indent=2),
            research_design_json=json.dumps(prev.get("step_3", {}), indent=2),
            selected_metrics_json=json.dumps(
                prev.get("step_3", {}).get("selected_metrics", []), indent=2
            ),
        )

        # Call LLM
        raw_result = await self.llm.generate_json(prompt)

        # Parse into QuestionnaireContent for validation
        content = QuestionnaireContent(**raw_result)

        # Re-calculate duration deterministically
        content.estimated_duration_minutes = self.estimate_duration(content.sections)

        # Recount questions
        content.total_questions = sum(
            len(s.questions) for s in content.sections
        )

        # Run validation
        warnings = self.validate_questionnaire(content)

        # Transition study state: step_3_locked -> step_4_draft -> step_4_review
        StudyStateMachine.transition(study, "step_4_draft")
        StudyStateMachine.transition(study, "step_4_review")

        # Determine version number
        existing = await self._load_step_version(study_id, 4, db)
        version = (existing.version + 1) if existing else 1

        # Create StepVersion record
        sv = StepVersion(
            id=uuid.uuid4(),
            study_id=study_id,
            step=4,
            version=version,
            status="review",
            content=content.model_dump(),
            ai_rationale={"warnings": warnings},
            created_at=datetime.now(timezone.utc),
        )
        db.add(sv)
        await db.commit()
        await db.refresh(sv)

        return self._step_version_to_response(sv)

    # ── edit_questionnaire (CRUD) ───────────────────────────────────────

    async def edit_questionnaire(
        self,
        study_id: uuid.UUID,
        operations: list[dict],
        db: AsyncSession,
    ) -> StepVersionResponse:
        """Apply CRUD operations to the questionnaire and create a new version.

        Operations:
        - update_question: { type, question_id, updates: { question_text, scale, ... } }
        - delete_question: { type, question_id }
        - add_question:    { type, section_id, question: { ... } }
        """
        study = await self._load_study(study_id, db)

        if StudyStateMachine.is_step_locked(study, 4):
            raise ValueError("Cannot edit questionnaire: step 4 is already locked")

        current_sv = await self._load_step_version(study_id, 4, db)
        if current_sv is None:
            raise ValueError("No questionnaire found. Generate one first.")

        questionnaire = QuestionnaireContent(**current_sv.content)

        for op in operations:
            op_type = op.get("type")
            if op_type == "update_question":
                self._apply_update_question(questionnaire, op)
            elif op_type == "delete_question":
                self._apply_delete_question(questionnaire, op)
            elif op_type == "add_question":
                self._apply_add_question(questionnaire, op)
            else:
                raise ValueError(f"Unknown operation type: {op_type}")

        # Recalculate duration and question count
        questionnaire.estimated_duration_minutes = self.estimate_duration(questionnaire.sections)
        questionnaire.total_questions = sum(len(s.questions) for s in questionnaire.sections)

        # New version
        new_version = current_sv.version + 1
        questionnaire.version = new_version

        sv = StepVersion(
            id=uuid.uuid4(),
            study_id=study_id,
            step=4,
            version=new_version,
            status="review",
            content=questionnaire.model_dump(),
            ai_rationale={"change_log": [f"Applied {len(operations)} edit(s)"]},
            created_at=datetime.now(timezone.utc),
        )
        db.add(sv)
        await db.commit()
        await db.refresh(sv)

        return self._step_version_to_response(sv)

    @staticmethod
    def _apply_update_question(questionnaire: QuestionnaireContent, op: dict) -> None:
        question_id = op.get("question_id")
        updates = op.get("updates", {})
        for section in questionnaire.sections:
            for q in section.questions:
                if q.question_id == question_id:
                    for key, value in updates.items():
                        if hasattr(q, key):
                            setattr(q, key, value)
                    return
        raise ValueError(f"Question '{question_id}' not found")

    @staticmethod
    def _apply_delete_question(questionnaire: QuestionnaireContent, op: dict) -> None:
        question_id = op.get("question_id")
        for section in questionnaire.sections:
            for i, q in enumerate(section.questions):
                if q.question_id == question_id:
                    section.questions.pop(i)
                    # Re-number positions
                    for j, remaining in enumerate(section.questions):
                        remaining.position_in_section = j + 1
                    return
        raise ValueError(f"Question '{question_id}' not found")

    @staticmethod
    def _apply_add_question(questionnaire: QuestionnaireContent, op: dict) -> None:
        section_id = op.get("section_id")
        question_data = op.get("question", {})
        for section in questionnaire.sections:
            if section.section_id == section_id:
                position = len(section.questions) + 1
                question_data["position_in_section"] = position
                question_data["section"] = section_id
                if "question_id" not in question_data:
                    question_data["question_id"] = f"Q_new_{position}"
                from app.schemas.questionnaire import Question
                new_q = Question(**question_data)
                section.questions.append(new_q)
                return
        raise ValueError(f"Section '{section_id}' not found")

    # ── submit_section_feedback ──────────────────────────────────────────

    async def submit_section_feedback(
        self,
        study_id: uuid.UUID,
        feedback: SectionFeedbackRequest,
        db: AsyncSession,
    ) -> SectionFeedbackResponse:
        """Incorporate feedback into a specific section of the questionnaire.

        Pre-conditions:
        - Step 4 must NOT be locked.
        """
        study = await self._load_study(study_id, db)

        # Step 4 must not be locked
        if StudyStateMachine.is_step_locked(study, 4):
            raise ValueError("Cannot edit questionnaire: step 4 is already locked")

        # Load current questionnaire
        current_sv = await self._load_step_version(study_id, 4, db)
        if current_sv is None:
            raise ValueError("No questionnaire found for this study. Generate one first.")

        questionnaire = QuestionnaireContent(**current_sv.content)

        # Find target section
        target_section = None
        for section in questionnaire.sections:
            if section.section_id == feedback.section_id:
                target_section = section
                break

        if target_section is None:
            raise ValueError(f"Section '{feedback.section_id}' not found in questionnaire")

        # Build the prompt
        prompt = self.prompts.format_prompt(
            "feedback_incorporator",
            section_json=json.dumps(target_section.model_dump(), indent=2),
            feedback_text=feedback.feedback_text,
            feedback_type=feedback.feedback_type,
            question_id=feedback.target_question_id or "N/A",
        )

        # Call LLM
        raw_result = await self.llm.generate_json(prompt)

        # Parse the response
        feedback_response = SectionFeedbackResponse(**raw_result)

        # Replace section in questionnaire
        updated_sections = []
        for section in questionnaire.sections:
            if section.section_id == feedback.section_id:
                updated_sections.append(feedback_response.updated_section)
            else:
                updated_sections.append(section)
        questionnaire.sections = updated_sections

        # Recalculate duration and question count
        questionnaire.estimated_duration_minutes = self.estimate_duration(
            questionnaire.sections
        )
        questionnaire.total_questions = sum(
            len(s.questions) for s in questionnaire.sections
        )

        # Increment version
        new_version = current_sv.version + 1
        questionnaire.version = new_version

        # Create new StepVersion record
        sv = StepVersion(
            id=uuid.uuid4(),
            study_id=study_id,
            step=4,
            version=new_version,
            status="review",
            content=questionnaire.model_dump(),
            ai_rationale={
                "change_log": feedback_response.change_log,
                "warnings": feedback_response.warnings,
            },
            created_at=datetime.now(timezone.utc),
        )
        db.add(sv)
        await db.commit()
        await db.refresh(sv)

        return feedback_response

    # ── lock_questionnaire ───────────────────────────────────────────────

    async def lock_questionnaire(
        self,
        study_id: uuid.UUID,
        user_id: str,
        db: AsyncSession,
    ) -> StepVersionResponse:
        """Lock step 4 and transition study to 'complete'.

        Pre-conditions:
        - Study must be in step_4_review.
        """
        study = await self._load_study(study_id, db)

        # Lock the step using the state machine
        StudyStateMachine.lock_step(study, 4, user_id)

        # Transition to complete
        StudyStateMachine.transition(study, "complete")

        # Update the latest StepVersion
        current_sv = await self._load_step_version(study_id, 4, db)
        if current_sv is None:
            raise ValueError("No questionnaire found to lock")

        current_sv.status = "locked"
        current_sv.locked_at = datetime.now(timezone.utc)
        try:
            current_sv.locked_by = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        except ValueError:
            current_sv.locked_by = None

        await db.commit()
        await db.refresh(study)
        await db.refresh(current_sv)

        return self._step_version_to_response(current_sv)

    # ── estimate_duration (deterministic) ────────────────────────────────

    @staticmethod
    def estimate_duration(sections: list[QuestionnaireSection]) -> int:
        """Calculate estimated survey duration in minutes (rounded up).

        Time per question type (seconds):
        - single_select: 15
        - multi_select: 20
        - open_text: 60
        - rating: 15
        - ranking: 30
        - concept_exposure: 30

        Adds a 60-second buffer. Returns total in minutes (ceiling).
        """
        total_seconds = 0
        for section in sections:
            for question in section.questions:
                total_seconds += DURATION_SECONDS.get(question.question_type, 15)
        total_seconds += DURATION_BUFFER_SECONDS
        return math.ceil(total_seconds / 60)

    # ── validate_questionnaire ───────────────────────────────────────────

    @staticmethod
    def validate_questionnaire(content: QuestionnaireContent) -> list[str]:
        """Validate a questionnaire and return a list of warning strings.

        Checks performed:
        1. Duration > 20 minutes
        2. Purchase Intent (PI) not first in S4_core_kpi
        3. More than 2 open-ended questions per concept exposure section
        4. Missing attention check
        5. Demographics not last section
        6. Leading question detection (superlatives / loaded language)
        7. Screening section mismatch (missing S1_screening)
        """
        warnings: list[str] = []

        # 1. Duration check
        if content.estimated_duration_minutes > 20:
            warnings.append(
                f"Questionnaire duration ({content.estimated_duration_minutes} min) "
                f"exceeds recommended maximum of 20 minutes"
            )

        # 2. PI not first in KPI section
        kpi_section = None
        for section in content.sections:
            if section.section_id == "S4_core_kpi":
                kpi_section = section
                break

        if kpi_section and kpi_section.questions:
            first_q = kpi_section.questions[0]
            # Check if the first question is Purchase Intent
            is_pi = (
                first_q.metric_id
                and "purchase_intent" in first_q.metric_id.lower()
            ) or (
                "purchase intent" in first_q.question_text.get("en", "").lower()
            )
            if not is_pi:
                warnings.append(
                    "Purchase Intent (PI) must be the first question in S4_core_kpi "
                    "to avoid priming effects"
                )

        # 3. More than 2 open-ended per concept section
        for section in content.sections:
            if section.section_id.startswith("S3_concept"):
                open_count = sum(
                    1 for q in section.questions if q.question_type == "open_text"
                )
                if open_count > 2:
                    warnings.append(
                        f"{section.section_id} has {open_count} open-text questions; "
                        f"maximum recommended is 2 per concept"
                    )

        # 4. Missing attention check
        has_attention_check = False
        for section in content.sections:
            for q in section.questions:
                if q.design_notes and "ATTENTION_CHECK" in q.design_notes.upper():
                    has_attention_check = True
                    break
            if has_attention_check:
                break

        if not has_attention_check:
            warnings.append(
                "No attention check question found. Include at least one question "
                "with design_notes containing 'ATTENTION_CHECK'"
            )

        # 5. Demographics not last
        if content.sections:
            last_section = content.sections[-1]
            if last_section.section_id != "S8_demographics":
                warnings.append(
                    "Demographics (S8_demographics) must be the last section. "
                    f"Currently the last section is '{last_section.section_id}'"
                )

        # 6. Leading questions (check for superlatives and loaded language)
        leading_indicators = [
            "best",
            "amazing",
            "worst",
            "terrible",
            "obviously",
            "clearly",
            "everyone knows",
            "don't you think",
            "don't you agree",
            "surely",
            "of course",
        ]
        for section in content.sections:
            for q in section.questions:
                text = q.question_text.get("en", "").lower()
                for indicator in leading_indicators:
                    if indicator in text:
                        warnings.append(
                            f"Potential leading question detected in {q.question_id}: "
                            f"contains '{indicator}'. Rephrase for neutrality."
                        )

        # 7. Screening section mismatch
        has_screening = any(
            s.section_id == "S1_screening" for s in content.sections
        )
        if not has_screening:
            warnings.append(
                "Missing S1_screening section. Screening questions are required "
                "to match the research design target audience."
            )

        return warnings
