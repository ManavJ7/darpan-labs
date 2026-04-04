"""Core interview orchestration service."""

import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm import LLMClient, get_llm_client
from app.models.interview import InterviewModule, InterviewSession, InterviewTurn
from app.models.consent import ConsentEvent
from app.models.user import User
from app.schemas.interview import (
    ConsentData,
    FirstQuestion,
    InterviewAnswerRequest,
    InterviewAnswerResponse,
    InterviewNextQuestionResponse,
    InterviewPauseResponse,
    InterviewSkipRequest,
    InterviewStartRequest,
    InterviewStartResponse,
    InterviewStatusResponse,
    ModuleCompleteResponse,
    ModuleInfo,
    ModulePlanItem,
    ModuleProgress,
    OptionItemSchema,
    QuestionMeta,
    StartSingleModuleRequest,
    UserModulesResponse,
    UserModuleStatus,
)
from app.schemas.llm_responses import (
    AcknowledgmentResponse,
    AdaptiveQuestionResult,
    FollowUpProbeResponse,
)
from app.services.answer_parser_service import (
    AnswerParserService,
    get_answer_parser_service,
)
from app.services.module_state_service import (
    ModuleStateService,
    get_module_state_service,
)
from app.services.prompt_service import PromptService, get_prompt_service
from app.services.question_bank_service import (
    MODULE_FILES,
    Question,
    QuestionBankService,
    get_question_bank_service,
)

logger = logging.getLogger(__name__)


def _rich_fields_from_question(
    question: Question,
    question_bank: "QuestionBankService | None" = None,
    module_id: str | None = None,
) -> dict:
    """Extract rich UI fields from a Question into a dict for schemas.

    Returns plain dicts/lists (JSON-serializable) so the result can be
    stored in JSONB columns *and* unpacked into Pydantic schema kwargs.
    """
    fields: dict = {}
    if question.options:
        fields["options"] = [
            {"label": o.label, "value": o.value} for o in question.options
        ]
    if question.max_selections is not None:
        fields["max_selections"] = question.max_selections
    if question.scale_min is not None:
        fields["scale_min"] = question.scale_min
    if question.scale_max is not None:
        fields["scale_max"] = question.scale_max
    if question.scale_labels:
        fields["scale_labels"] = question.scale_labels
    if question.matrix_items:
        fields["matrix_items"] = question.matrix_items
    if question.matrix_options:
        fields["matrix_options"] = [
            {"label": o.label, "value": o.value} for o in question.matrix_options
        ]
    if question.placeholder:
        fields["placeholder"] = question.placeholder
    # Concept card lookup
    if question.concept_ref and question_bank and module_id:
        concept = question_bank.get_concept_card(module_id, question.concept_ref)
        if concept:
            fields["concept_card"] = {
                "concept_id": question.concept_ref,
                "name": concept.name,
                "consumer_insight": concept.consumer_insight,
                "key_benefit": concept.key_benefit,
                "how_it_works": concept.how_it_works,
                "packaging": concept.packaging,
                "price": concept.price,
            }
    return fields


class InterviewService:
    """Core interview orchestration service."""

    def __init__(
        self,
        question_bank: QuestionBankService | None = None,
        module_state: ModuleStateService | None = None,
        answer_parser: AnswerParserService | None = None,
        prompt_service: PromptService | None = None,
        llm_client: LLMClient | None = None,
    ):
        """Initialize interview service.

        Args:
            question_bank: Service for loading question banks.
            module_state: Service for tracking module state.
            answer_parser: Service for parsing answers.
            prompt_service: Service for loading prompts.
            llm_client: LLM client for generating questions.
        """
        self.question_bank = question_bank or get_question_bank_service()
        self.module_state = module_state or get_module_state_service()
        self.answer_parser = answer_parser or get_answer_parser_service()
        self.prompt_service = prompt_service or get_prompt_service()
        self.llm_client = llm_client or get_llm_client()

    async def start_interview(
        self,
        session: AsyncSession,
        request: InterviewStartRequest,
    ) -> InterviewStartResponse:
        """Create new interview session with modules initialized.

        Args:
            session: Database session.
            request: Interview start request.

        Returns:
            InterviewStartResponse with session info and first question.
        """
        # Ensure user exists (auto-create for demo purposes)
        await self._ensure_user_exists(session, request.user_id)

        # Create interview session
        interview_session = InterviewSession(
            user_id=request.user_id,
            status="active",
            input_mode=request.input_mode,
            language_preference=request.language_preference,
            settings={
                "sensitivity_settings": request.sensitivity_settings.model_dump(),
                "modules_to_complete": request.modules_to_complete,
            },
        )
        session.add(interview_session)
        await session.flush()

        # Record consent if provided
        if request.consent:
            await self._record_consent(session, request.user_id, request.consent)

        # Initialize modules
        modules = await self.module_state.initialize_modules(
            session,
            interview_session.id,
            request.modules_to_complete,
        )

        # Get first module and question
        first_module = modules[0]
        first_question = self.question_bank.get_first_question(first_module.module_id)

        # Create first interviewer turn
        await self._create_interviewer_turn(
            session,
            interview_session.id,
            first_module.module_id,
            first_question,
            turn_index=0,
        )

        # Build response
        module_plan = self._build_module_plan(modules)
        bank = self.question_bank.load_question_bank(first_module.module_id)
        first_module_info = ModuleInfo(
            module_id=first_module.module_id,
            module_name=self.question_bank.get_module_name(first_module.module_id),
            estimated_duration_min=bank.estimated_duration_min,
            total_questions=len(bank.questions),
            status="active",
        )

        logger.info(f"Started interview session {interview_session.id}")

        return InterviewStartResponse(
            session_id=interview_session.id,
            status="active",
            first_module=first_module_info,
            module_plan=module_plan,
            first_question=FirstQuestion(
                question_id=first_question.question_id,
                question_text=first_question.question_text,
                question_type=first_question.question_type,
                target_signal=first_question.target_signals[0]
                if first_question.target_signals
                else "",
                **_rich_fields_from_question(first_question, self.question_bank, first_module.module_id),
            ),
        )

    async def submit_answer(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
        request: InterviewAnswerRequest,
    ) -> InterviewAnswerResponse:
        """Process and persist user answer.

        Args:
            session: Database session.
            interview_session_id: Interview session ID.
            request: Answer submission request.

        Returns:
            InterviewAnswerResponse confirming answer receipt.
        """
        # Get active module
        active_module = await self.module_state.get_active_module(
            session, interview_session_id
        )
        if not active_module:
            raise ValueError("No active module for this session")

        # Get last interviewer turn to know the question
        last_turn = await self._get_last_turn(session, interview_session_id)
        if not last_turn or last_turn.role != "interviewer":
            raise ValueError("Expected interviewer turn before answer")

        # Get next turn index
        turn_index = last_turn.turn_index + 1

        # Create user turn
        user_turn = InterviewTurn(
            session_id=interview_session_id,
            module_id=active_module.module_id,
            turn_index=turn_index,
            role="user",
            input_mode=request.input_mode,
            answer_text=request.answer_text,
            question_meta=last_turn.question_meta,  # Copy question context
            audio_meta=request.audio_meta,
        )
        session.add(user_turn)
        await session.flush()

        # Check satisfaction only for open-text questions (drives follow-up probes)
        # Skip for concept test module — pure structured survey, no follow-ups
        last_question_type = (last_turn.question_meta or {}).get("question_type", "")
        if active_module.module_id == "M8":
            is_satisfactory, reason = True, None
        elif last_question_type in ("open_text", "scale_open"):
            question_text = last_turn.question_text or ""
            target_signal = (last_turn.question_meta or {}).get("target_signal", "")
            is_satisfactory, reason = await self.answer_parser.is_answer_satisfactory(
                question_text=question_text,
                answer_text=request.answer_text,
                target_signal=target_signal,
            )
        else:
            is_satisfactory, reason = True, None

        # Store satisfaction result in answer_meta
        user_turn.answer_meta = {
            "is_satisfactory": is_satisfactory,
            "unsatisfactory_reason": reason,
        }

        # Update module state (just increment question count)
        await self.module_state.update_module_after_answer(session, active_module)

        logger.debug(f"Submitted answer for turn {turn_index}")

        return InterviewAnswerResponse(
            turn_id=user_turn.id,
            answer_received=True,
            answer_meta=user_turn.answer_meta,
        )

    async def get_next_question(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
    ) -> InterviewNextQuestionResponse:
        """Get next question using adaptive selection.

        Args:
            session: Database session.
            interview_session_id: Interview session ID.

        Returns:
            InterviewNextQuestionResponse with next question or completion status.
        """
        # Get active module
        active_module = await self.module_state.get_active_module(
            session, interview_session_id
        )
        if not active_module:
            # Check if interview is complete
            interview = await self._get_interview_session(session, interview_session_id)
            if interview and interview.status == "completed":
                return self._build_all_complete_response()
            raise ValueError("No active module for this session")

        # Evaluate module completion
        completion = await self.module_state.evaluate_module_completion(
            session, interview_session_id, active_module.module_id
        )

        if completion.is_complete:
            # Transition to next module
            next_module = await self.module_state.transition_to_next_module(
                session,
                interview_session_id,
                active_module.module_id,
                completion.module_summary,
            )

            if next_module is None:
                # All modules complete
                await self._mark_interview_complete(session, interview_session_id)
                return self._build_module_complete_response(
                    active_module,
                    completion.module_summary,
                    all_complete=True,
                )

            # Get first question for new module
            first_question = self.question_bank.get_first_question(next_module.module_id)
            turn_index = await self._get_next_turn_index(session, interview_session_id)

            await self._create_interviewer_turn(
                session,
                interview_session_id,
                next_module.module_id,
                first_question,
                turn_index,
            )

            return self._build_module_complete_response(
                active_module,
                completion.module_summary,
                next_question=first_question,
                next_module=next_module,
            )

        # Get next question (hybrid: deterministic base + LLM follow-up)
        question_result = await self._get_next_question_hybrid(
            session, interview_session_id, active_module
        )

        if question_result.action == "MODULE_COMPLETE":
            # LLM decided module is complete
            return await self._handle_module_complete(
                session,
                interview_session_id,
                active_module,
                question_result.module_summary,
            )

        # Create interviewer turn
        turn_index = await self._get_next_turn_index(session, interview_session_id)
        await self._create_adaptive_turn(
            session,
            interview_session_id,
            active_module.module_id,
            question_result,
            turn_index,
        )

        return self._build_continue_response(active_module, question_result)

    async def skip_question(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
        request: InterviewSkipRequest,
    ) -> InterviewNextQuestionResponse:
        """Skip current question and get next.

        Args:
            session: Database session.
            interview_session_id: Interview session ID.
            request: Skip request with optional reason.

        Returns:
            InterviewNextQuestionResponse with next question.
        """
        # Get active module
        active_module = await self.module_state.get_active_module(
            session, interview_session_id
        )
        if not active_module:
            raise ValueError("No active module for this session")

        # Get last turn
        last_turn = await self._get_last_turn(session, interview_session_id)
        if not last_turn or last_turn.role != "interviewer":
            raise ValueError("Expected interviewer turn to skip")

        # Create skip turn
        turn_index = last_turn.turn_index + 1
        skip_turn = InterviewTurn(
            session_id=interview_session_id,
            module_id=active_module.module_id,
            turn_index=turn_index,
            role="user",
            input_mode="text",
            answer_text="[SKIPPED]",
            question_meta=last_turn.question_meta,
            answer_meta={"skipped": True, "skip_reason": request.reason},
        )
        session.add(skip_turn)
        await session.flush()

        logger.debug(f"Skipped question at turn {turn_index}")

        # Get next question
        return await self.get_next_question(session, interview_session_id)

    async def pause_interview(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
    ) -> InterviewPauseResponse:
        """Pause interview for later resumption.

        Args:
            session: Database session.
            interview_session_id: Interview session ID.

        Returns:
            InterviewPauseResponse with resume info.
        """
        interview = await self._get_interview_session(session, interview_session_id)
        if not interview:
            raise ValueError("Interview session not found")

        interview.status = "paused"

        # Get current position
        active_module = await self.module_state.get_active_module(
            session, interview_session_id
        )
        last_turn = await self._get_last_turn(session, interview_session_id)

        module_id = active_module.module_id if active_module else "M1"
        question_index = last_turn.turn_index if last_turn else 0

        await session.flush()
        logger.info(f"Paused interview {interview_session_id}")

        return InterviewPauseResponse(
            session_id=interview_session_id,
            status="paused",
            can_resume=True,
            resume_at_module=module_id,
            resume_at_question=question_index,
        )

    async def resume_interview(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
    ) -> InterviewStartResponse:
        """Resume paused interview from last position.

        Args:
            session: Database session.
            interview_session_id: Interview session ID.

        Returns:
            InterviewStartResponse with current state.
        """
        interview = await self._get_interview_session(session, interview_session_id)
        if not interview:
            raise ValueError("Interview session not found")

        if interview.status not in ("paused", "active"):
            raise ValueError(f"Cannot resume interview with status: {interview.status}")

        interview.status = "active"

        # Get current module
        active_module = await self.module_state.get_active_module(
            session, interview_session_id
        )
        if not active_module:
            # Find first non-completed module
            modules = await self.module_state.get_all_modules(
                session, interview_session_id
            )
            for m in modules:
                if m.status != "completed":
                    m.status = "active"
                    active_module = m
                    break

        if not active_module:
            raise ValueError("All modules completed, cannot resume")

        # Get last turn to determine current question
        last_turn = await self._get_last_turn(session, interview_session_id)

        # Determine current question
        if last_turn and last_turn.role == "interviewer":
            # Last turn was a question, return it with rich fields from bank
            q_id = (last_turn.question_meta or {}).get("question_id", "")
            rich: dict = {}
            if q_id and not q_id.startswith("adaptive_"):
                orig_q = self.question_bank.get_question_by_id(
                    active_module.module_id, q_id
                )
                if orig_q:
                    rich = _rich_fields_from_question(orig_q, self.question_bank, active_module.module_id)
            current_question = FirstQuestion(
                question_id=q_id,
                question_text=last_turn.question_text or "",
                question_type=(last_turn.question_meta or {}).get(
                    "question_type", "open_text"
                ),
                target_signal=(last_turn.question_meta or {}).get("target_signal", ""),
                **rich,
            )
        else:
            # Need to generate next question
            question = self.question_bank.get_next_static_question(
                active_module.module_id,
                await self._get_asked_question_ids(
                    session, interview_session_id, active_module.module_id
                ),
            )
            if not question:
                question = self.question_bank.get_first_question(active_module.module_id)

            turn_index = await self._get_next_turn_index(session, interview_session_id)
            await self._create_interviewer_turn(
                session,
                interview_session_id,
                active_module.module_id,
                question,
                turn_index,
            )

            current_question = FirstQuestion(
                question_id=question.question_id,
                question_text=question.question_text,
                question_type=question.question_type,
                target_signal=question.target_signals[0]
                if question.target_signals
                else "",
                **_rich_fields_from_question(question, self.question_bank, active_module.module_id),
            )

        # Build response
        modules = await self.module_state.get_all_modules(session, interview_session_id)
        module_plan = self._build_module_plan_from_db(modules)

        await session.flush()
        logger.info(f"Resumed interview {interview_session_id}")

        resume_bank = self.question_bank.load_question_bank(active_module.module_id)
        return InterviewStartResponse(
            session_id=interview_session_id,
            status="active",
            first_module=ModuleInfo(
                module_id=active_module.module_id,
                module_name=self.question_bank.get_module_name(active_module.module_id),
                estimated_duration_min=resume_bank.estimated_duration_min,
                total_questions=len(resume_bank.questions),
                status="active",
            ),
            module_plan=module_plan,
            first_question=current_question,
        )

    async def get_interview_status(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
    ) -> InterviewStatusResponse:
        """Get full interview status with all module progress.

        Args:
            session: Database session.
            interview_session_id: Interview session ID.

        Returns:
            InterviewStatusResponse with complete status.
        """
        interview = await self._get_interview_session(session, interview_session_id)
        if not interview:
            raise ValueError("Interview session not found")

        modules = await self.module_state.get_all_modules(session, interview_session_id)
        active_module = next((m for m in modules if m.status == "active"), None)

        # Calculate total duration
        if interview.ended_at:
            duration = int((interview.ended_at - interview.started_at).total_seconds())
        else:
            duration = int(
                (datetime.now(timezone.utc) - interview.started_at).total_seconds()
            )

        module_progress = [
            self._build_module_progress(m)
            for m in modules
        ]

        return InterviewStatusResponse(
            session_id=interview_session_id,
            status=interview.status,
            input_mode=interview.input_mode,
            language_preference=interview.language_preference,
            started_at=interview.started_at,
            total_duration_sec=duration,
            modules=module_progress,
            current_module=active_module.module_id if active_module else None,
            completed_modules=[m.module_id for m in modules if m.status == "completed"],
        )

    # ========== Private Helper Methods ==========

    async def _ensure_user_exists(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> User:
        """Ensure user exists (created via auth flow).

        Args:
            session: Database session.
            user_id: User ID to look up.

        Returns:
            User instance.

        Raises:
            ValueError: If user not found.
        """
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise ValueError(f"User {user_id} not found. Please sign in first.")

        return user

    async def _get_next_question_hybrid(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
        module: InterviewModule,
    ) -> AdaptiveQuestionResult:
        """Get next question using sequential + follow-up logic.

        Two paths:
        1. FOLLOW-UP PATH: If last answer was unsatisfactory and we haven't
           exhausted follow-up attempts (max 2), use LLM to generate a probe.
        2. NEXT QUESTION PATH: If answer was satisfactory (or max follow-ups
           reached), pick next question sequentially from the bank.

        Args:
            session: Database session.
            interview_session_id: Interview session ID.
            module: Current module.

        Returns:
            AdaptiveQuestionResult with question details.
        """
        last_turn = await self._get_last_user_turn(session, interview_session_id)
        answer_meta = (last_turn.answer_meta or {}) if last_turn else {}
        is_satisfactory = answer_meta.get("is_satisfactory", True)
        unsatisfactory_reason = answer_meta.get("unsatisfactory_reason")
        consecutive_followups = await self._count_consecutive_followups(
            session, interview_session_id
        )

        # FOLLOW-UP PATH: only for open-text questions, skip for concept test module
        last_question_type = (last_turn.question_meta or {}).get("question_type", "") if last_turn else ""
        is_open_text = last_question_type in ("open_text", "scale_open")
        if is_open_text and not is_satisfactory and consecutive_followups < 2 and module.module_id != "M8":
            return await self._generate_followup_probe(
                session,
                interview_session_id,
                module,
                last_turn,
                unsatisfactory_reason,
                consecutive_followups,
            )

        # NEXT QUESTION PATH: move to next bank question
        return await self._get_deterministic_next(session, module, last_turn)

    async def _get_deterministic_next(
        self,
        session: AsyncSession,
        module: InterviewModule,
        last_turn: InterviewTurn | None = None,
    ) -> AdaptiveQuestionResult:
        """Pick next question sequentially from the bank."""
        asked_ids = await self._get_asked_question_ids(
            session, module.session_id, module.module_id
        )

        next_question = self.question_bank.get_next_static_question(
            module_id=module.module_id,
            asked_question_ids=asked_ids,
        )

        if next_question is None:
            # All questions exhausted → module complete
            return AdaptiveQuestionResult(
                action="MODULE_COMPLETE",
                question_text="",
                language="EN",
                question_type="open_text",
                target_signal="",
                rationale="All bank questions asked",
                module_summary="Module completed.",
            )

        return AdaptiveQuestionResult(
            action="ASK_QUESTION",
            question_text=next_question.question_text,
            language="EN",
            question_type=next_question.question_type,
            target_signal=next_question.target_signals[0]
            if next_question.target_signals
            else "",
            rationale="Sequential question from bank",
            question_intent="EXPLORE",
            question_id=next_question.question_id,
        )

    async def _generate_followup_probe(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
        module: InterviewModule,
        last_turn: InterviewTurn,
        followup_reason: str | None,
        consecutive_followups: int,
    ) -> AdaptiveQuestionResult:
        """LLM generates a targeted follow-up when the answer was vague."""
        question_meta = last_turn.question_meta or {}
        # Fetch module goal for richer context
        try:
            module_goal = self.question_bank.get_module_goal(module.module_id)
        except (FileNotFoundError, ValueError):
            module_goal = ""
        try:
            prompt = self.prompt_service.get_followup_probe_prompt(
                question_text=last_turn.question_text or question_meta.get("question_text", ""),
                target_signal=question_meta.get("target_signal", ""),
                answer_text=last_turn.answer_text or "",
                followup_attempt=consecutive_followups + 1,
                followup_reason=followup_reason or "vague_answer",
                previous_context=await self._get_brief_context(session, interview_session_id),
                module_goal=module_goal,
            )
            response = await self.llm_client.generate(
                prompt=prompt,
                response_format=FollowUpProbeResponse,
                temperature=0.5,
                max_tokens=200,
            )
            return AdaptiveQuestionResult(
                action="ASK_FOLLOWUP",
                question_text=response.followup_question,
                language="EN",
                question_type="open_text",
                target_signal=question_meta.get("target_signal", ""),
                rationale=f"Follow-up probe #{consecutive_followups + 1}: {followup_reason}",
                question_intent=response.followup_intent,
                acknowledgment_text=response.acknowledgment_text,
                is_followup=True,
            )
        except Exception as e:
            logger.warning(f"Follow-up probe LLM failed, moving on: {e}")
            # Graceful degradation: move to next bank question
            return await self._get_deterministic_next(session, module, last_turn)

    async def _generate_acknowledgment(
        self,
        answer_text: str,
        question_text: str,
    ) -> str | None:
        """Generate warm acknowledgment text (small LLM call)."""
        try:
            prompt = self.prompt_service.get_acknowledgment_prompt(
                answer_text=answer_text,
                question_text=question_text,
            )
            response = await self.llm_client.generate(
                prompt=prompt,
                response_format=AcknowledgmentResponse,
                temperature=0.5,
                max_tokens=100,
            )
            return response.acknowledgment_text
        except Exception:
            return None  # Graceful degradation

    async def _count_consecutive_followups(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
    ) -> int:
        """Count consecutive ASK_FOLLOWUP actions in recent turns.

        Reads interviewer turns backward. Returns 0 if the last
        interviewer action was ASK_QUESTION.
        """
        result = await session.execute(
            select(InterviewTurn)
            .where(
                InterviewTurn.session_id == interview_session_id,
                InterviewTurn.role == "interviewer",
            )
            .order_by(InterviewTurn.turn_index.desc())
            .limit(5)
        )
        turns = list(result.scalars().all())

        count = 0
        for turn in turns:
            meta = turn.question_meta or {}
            if meta.get("is_followup"):
                count += 1
            else:
                break
        return count

    async def _get_last_user_turn(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
    ) -> InterviewTurn | None:
        """Get the last user (answer) turn for a session."""
        result = await session.execute(
            select(InterviewTurn)
            .where(
                InterviewTurn.session_id == interview_session_id,
                InterviewTurn.role == "user",
            )
            .order_by(InterviewTurn.turn_index.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_brief_context(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
        max_pairs: int = 3,
    ) -> str:
        """Get brief conversation context for follow-up probe."""
        result = await session.execute(
            select(InterviewTurn)
            .where(InterviewTurn.session_id == interview_session_id)
            .order_by(InterviewTurn.turn_index.desc())
            .limit(max_pairs * 2)
        )
        turns = list(reversed(result.scalars().all()))
        if not turns:
            return ""

        lines = []
        for t in turns:
            if t.role == "interviewer":
                lines.append(f"Q: {t.question_text}")
            else:
                lines.append(f"A: {t.answer_text}")
        return "Recent conversation:\n" + "\n".join(lines)

    async def _record_consent(
        self,
        session: AsyncSession,
        user_id: UUID,
        consent: ConsentData,
    ) -> None:
        """Record consent event."""
        event = ConsentEvent(
            user_id=user_id,
            consent_type="interview",
            consent_version=consent.consent_version,
            accepted=consent.accepted,
            consent_metadata={
                "allow_audio_storage_days": consent.allow_audio_storage_days,
                "allow_data_retention_days": consent.allow_data_retention_days,
            },
        )
        session.add(event)

    async def _create_interviewer_turn(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
        module_id: str,
        question: Question,
        turn_index: int,
    ) -> InterviewTurn:
        """Create an interviewer turn with a question."""
        meta: dict = {
            "question_id": question.question_id,
            "question_type": question.question_type,
            "target_signal": question.target_signals[0]
            if question.target_signals
            else "",
            "target_signals": question.target_signals,
            "is_followup": question.is_followup,
        }
        # Add rich UI fields for structured question types
        rich = _rich_fields_from_question(question)
        if rich:
            meta["rich"] = rich
        turn = InterviewTurn(
            session_id=interview_session_id,
            module_id=module_id,
            turn_index=turn_index,
            role="interviewer",
            input_mode="text",
            question_text=question.question_text,
            question_meta=meta,
        )
        session.add(turn)
        await session.flush()
        return turn

    async def _create_adaptive_turn(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
        module_id: str,
        question_result: AdaptiveQuestionResult,
        turn_index: int,
    ) -> InterviewTurn:
        """Create an interviewer turn from adaptive/hybrid question result."""
        # Use the static question_id if available, otherwise generate adaptive ID
        question_id = question_result.question_id or f"adaptive_{turn_index}"

        # Look up full target_signals from question bank if we have a real question ID
        target_signals = [question_result.target_signal] if question_result.target_signal else []
        if question_id and not question_id.startswith("adaptive_"):
            q = self.question_bank.get_question_by_id(module_id, question_id)
            if q:
                target_signals = q.target_signals

        turn = InterviewTurn(
            session_id=interview_session_id,
            module_id=module_id,
            turn_index=turn_index,
            role="interviewer",
            input_mode="text",
            question_text=question_result.question_text,
            question_meta={
                "question_id": question_id,
                "question_type": question_result.question_type,
                "target_signal": question_result.target_signal,
                "target_signals": target_signals,
                "is_followup": question_result.is_followup,
                "rationale": question_result.rationale,
                "acknowledgment_text": question_result.acknowledgment_text,
                "question_intent": question_result.question_intent,
            },
        )
        session.add(turn)
        await session.flush()
        return turn

    async def _get_interview_session(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
    ) -> InterviewSession | None:
        """Get interview session by ID."""
        result = await session.execute(
            select(InterviewSession).where(InterviewSession.id == interview_session_id)
        )
        return result.scalar_one_or_none()

    async def _get_last_turn(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
    ) -> InterviewTurn | None:
        """Get the last turn for a session."""
        result = await session.execute(
            select(InterviewTurn)
            .where(InterviewTurn.session_id == interview_session_id)
            .order_by(InterviewTurn.turn_index.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_next_turn_index(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
    ) -> int:
        """Get the next turn index for a session."""
        last_turn = await self._get_last_turn(session, interview_session_id)
        return (last_turn.turn_index + 1) if last_turn else 0

    async def _get_asked_question_ids(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
        module_id: str,
    ) -> list[str]:
        """Get IDs of questions already asked in a module."""
        result = await session.execute(
            select(InterviewTurn.question_meta)
            .where(
                InterviewTurn.session_id == interview_session_id,
                InterviewTurn.module_id == module_id,
                InterviewTurn.role == "interviewer",
            )
        )
        asked = []
        for (meta,) in result:
            if meta and "question_id" in meta:
                asked.append(meta["question_id"])
        return asked

    async def _get_previous_answers(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
        module_id: str,
    ) -> list[dict]:
        """Get previous Q&A pairs for context."""
        result = await session.execute(
            select(InterviewTurn)
            .where(
                InterviewTurn.session_id == interview_session_id,
                InterviewTurn.module_id == module_id,
            )
            .order_by(InterviewTurn.turn_index)
        )
        turns = list(result.scalars().all())

        pairs = []
        for i in range(0, len(turns) - 1, 2):
            if turns[i].role == "interviewer" and turns[i + 1].role == "user":
                pairs.append(
                    {
                        "question": turns[i].question_text,
                        "answer": turns[i + 1].answer_text,
                    }
                )
        return pairs

    async def _get_recent_turns(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
        module_id: str,
        limit: int = 6,
    ) -> list[dict]:
        """Get recent turns for context."""
        result = await session.execute(
            select(InterviewTurn)
            .where(
                InterviewTurn.session_id == interview_session_id,
                InterviewTurn.module_id == module_id,
            )
            .order_by(InterviewTurn.turn_index.desc())
            .limit(limit)
        )
        turns = list(reversed(result.scalars().all()))

        return [
            {
                "role": t.role,
                "question": t.question_text if t.role == "interviewer" else None,
                "answer": t.answer_text if t.role == "user" else None,
            }
            for t in turns
        ]

    async def _mark_interview_complete(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
    ) -> None:
        """Mark interview as complete."""
        interview = await self._get_interview_session(session, interview_session_id)
        if interview:
            interview.status = "completed"
            interview.ended_at = datetime.now(timezone.utc)
            interview.total_duration_sec = int(
                (interview.ended_at - interview.started_at).total_seconds()
            )

    async def _handle_module_complete(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
        module: InterviewModule,
        module_summary: str | None,
    ) -> InterviewNextQuestionResponse:
        """Handle module completion transition."""
        next_module = await self.module_state.transition_to_next_module(
            session, interview_session_id, module.module_id, module_summary
        )

        if next_module is None:
            await self._mark_interview_complete(session, interview_session_id)
            return self._build_module_complete_response(
                module, module_summary, all_complete=True
            )

        first_question = self.question_bank.get_first_question(next_module.module_id)
        turn_index = await self._get_next_turn_index(session, interview_session_id)

        await self._create_interviewer_turn(
            session,
            interview_session_id,
            next_module.module_id,
            first_question,
            turn_index,
        )

        return self._build_module_complete_response(
            module, module_summary, next_question=first_question, next_module=next_module
        )

    def _build_module_plan(
        self, modules: list[InterviewModule]
    ) -> list[ModulePlanItem]:
        """Build module plan from InterviewModule list."""
        plan = []
        for m in modules:
            try:
                bank = self.question_bank.load_question_bank(m.module_id)
                est_min = bank.estimated_duration_min
            except (FileNotFoundError, ValueError):
                est_min = 5
            plan.append(ModulePlanItem(module_id=m.module_id, status=m.status, est_min=est_min))
        return plan

    def _build_module_plan_from_db(
        self, modules: list[InterviewModule]
    ) -> list[ModulePlanItem]:
        """Build module plan from database modules."""
        return self._build_module_plan(modules)

    def _build_continue_response(
        self,
        module: InterviewModule,
        question_result: AdaptiveQuestionResult,
    ) -> InterviewNextQuestionResponse:
        """Build response for continuing interview."""
        # Use static question_id if available, otherwise generate adaptive ID
        question_id = question_result.question_id or f"adaptive_{module.question_count}"

        # Look up original Question from bank for rich fields
        rich: dict = {}
        if question_id and not question_id.startswith("adaptive_"):
            orig_q = self.question_bank.get_question_by_id(module.module_id, question_id)
            if orig_q:
                rich = _rich_fields_from_question(orig_q, self.question_bank, module.module_id)

        meta = QuestionMeta(
            question_id=question_id,
            question_type=question_result.question_type,
            target_signal=question_result.target_signal,
            rationale=question_result.rationale,
            is_followup=question_result.is_followup,
            **rich,
        )
        return InterviewNextQuestionResponse(
            question_id=question_id,
            question_text=question_result.question_text,
            question_type=question_result.question_type,
            question_meta=meta,
            module_id=module.module_id,
            module_progress=self._build_module_progress(module),
            status="continue",
            acknowledgment_text=question_result.acknowledgment_text,
            **rich,
        )

    def _build_module_progress(self, module: InterviewModule) -> ModuleProgress:
        """Build ModuleProgress from an InterviewModule."""
        bank = self.question_bank.load_question_bank(module.module_id)
        total = len(bank.questions)
        return ModuleProgress(
            module_id=module.module_id,
            module_name=self.question_bank.get_module_name(module.module_id),
            questions_asked=module.question_count,
            total_questions=total,
            coverage_score=module.question_count / max(total, 1),
            confidence_score=1.0 if module.status == "completed" else 0.0,
            signals_captured=[],
            status=module.status,
        )

    def _build_module_complete_response(
        self,
        module: InterviewModule,
        module_summary: str | None,
        next_question: Question | None = None,
        next_module: InterviewModule | None = None,
        all_complete: bool = False,
    ) -> InterviewNextQuestionResponse:
        """Build response for module completion."""
        status = "all_modules_complete" if all_complete else "module_complete"

        progress = self._build_module_progress(module)
        progress.status = "completed"
        progress.coverage_score = 1.0
        progress.confidence_score = 1.0

        response = InterviewNextQuestionResponse(
            module_id=module.module_id,
            module_progress=progress,
            status=status,
            module_summary=module_summary,
        )

        if next_question and next_module:
            rich = _rich_fields_from_question(next_question, self.question_bank, next_module.module_id)
            response.question_id = next_question.question_id
            response.question_text = next_question.question_text
            response.question_type = next_question.question_type
            response.question_meta = QuestionMeta(
                question_id=next_question.question_id,
                question_type=next_question.question_type,
                target_signal=next_question.target_signals[0]
                if next_question.target_signals
                else "",
                **rich,
            )
            response.module_id = next_module.module_id
            # Set top-level rich fields
            for k, v in rich.items():
                setattr(response, k, v)

        return response

    def _build_all_complete_response(self) -> InterviewNextQuestionResponse:
        """Build response when all modules are complete."""
        return InterviewNextQuestionResponse(
            module_id="",
            module_progress=ModuleProgress(
                module_id="",
                module_name="",
                questions_asked=0,
                total_questions=0,
                coverage_score=1.0,
                confidence_score=1.0,
                signals_captured=[],
                status="completed",
            ),
            status="all_modules_complete",
            module_summary="All interview modules completed successfully.",
        )

    # ========== Module-Based Onboarding Methods ==========

    async def get_user_modules(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> UserModulesResponse:
        """Get all module completion status for a user.

        Args:
            session: Database session.
            user_id: User ID.

        Returns:
            UserModulesResponse with all modules and their status.
        """
        # Ensure user exists
        await self._ensure_user_exists(session, user_id)

        # Get all completed modules across all sessions for this user
        result = await session.execute(
            select(InterviewModule, InterviewSession)
            .join(InterviewSession, InterviewModule.session_id == InterviewSession.id)
            .where(InterviewSession.user_id == user_id)
            .order_by(InterviewModule.ended_at.desc().nulls_last())
        )
        rows = result.all()

        # Track best completion for each module
        module_completions: dict[str, tuple[InterviewModule, InterviewSession]] = {}
        for module, interview_session in rows:
            if module.module_id not in module_completions:
                module_completions[module.module_id] = (module, interview_session)
            elif module.status == "completed" and module_completions[module.module_id][0].status != "completed":
                module_completions[module.module_id] = (module, interview_session)

        # Define all modules
        mandatory_modules = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"]
        all_modules = mandatory_modules
        module_info = {
            "M1": {"name": "Core Identity & Context", "description": "Demographics, personality, and consumer orientation"},
            "M2": {"name": "Preferences & Values", "description": "Value system, trust hierarchy, and brand attitudes"},
            "M3": {"name": "Purchase Decision Logic", "description": "How and where you buy, price sensitivity, and switching behavior"},
            "M4": {"name": "Lifestyle & Grooming", "description": "Daily bathing context, routines, and skin concerns"},
            "M5": {"name": "Sensory & Aesthetic Preferences", "description": "Fragrance, texture, lather, and packaging preferences"},
            "M6": {"name": "Body Wash Deep-Dive", "description": "Current brands, satisfaction, pain points, and unmet needs"},
            "M7": {"name": "Media & Influence", "description": "How you discover products and who you trust"},
            "M8": {"name": "Concept Test", "description": "Evaluate 5 product concepts and help pick the best 2 to develop"},
        }

        modules: list[UserModuleStatus] = []
        completed_count = 0

        for module_id in all_modules:
            if module_id in module_completions:
                module, interview_session = module_completions[module_id]
                if module.status == "completed":
                    status = "completed"
                    if module_id in mandatory_modules:
                        completed_count += 1
                elif module.status == "active":
                    status = "in_progress"
                else:
                    status = "not_started"

                modules.append(UserModuleStatus(
                    module_id=module_id,
                    module_name=module_info[module_id]["name"],
                    description=module_info[module_id]["description"],
                    status=status,
                    coverage_score=module.coverage_score if module.status == "completed" else None,
                    confidence_score=module.confidence_score if module.status == "completed" else None,
                    session_id=interview_session.id if module.status in ("completed", "active") else None,
                ))
            else:
                modules.append(UserModuleStatus(
                    module_id=module_id,
                    module_name=module_info[module_id]["name"],
                    description=module_info[module_id]["description"],
                    status="not_started",
                ))

        can_generate_twin = completed_count >= 8

        return UserModulesResponse(
            user_id=user_id,
            modules=modules,
            completed_count=completed_count,
            total_required=8,
            can_generate_twin=can_generate_twin,
        )

    async def start_single_module(
        self,
        session: AsyncSession,
        request: StartSingleModuleRequest,
    ) -> InterviewStartResponse:
        """Start a single module for a user.

        Args:
            session: Database session.
            request: Module start request.

        Returns:
            InterviewStartResponse with session info and first question.
        """
        # Validate module ID against registered question banks
        valid_modules = list(MODULE_FILES.keys())
        if request.module_id not in valid_modules:
            raise ValueError(f"Invalid module ID: {request.module_id}. Must be one of {valid_modules}")

        # Check if module is already completed or has an active/paused session
        user_modules = await self.get_user_modules(session, request.user_id)
        for mod in user_modules.modules:
            if mod.module_id == request.module_id:
                if mod.status == "completed":
                    raise ValueError(f"Module {request.module_id} is already completed")
                if mod.status == "in_progress" and mod.session_id:
                    # Resume existing session instead of creating a new one
                    logger.info(
                        f"Resuming existing session {mod.session_id} for module {request.module_id}"
                    )
                    return await self.resume_interview(session, mod.session_id)

        # Ensure user exists
        await self._ensure_user_exists(session, request.user_id)

        # Create interview session for this single module
        interview_session = InterviewSession(
            user_id=request.user_id,
            status="active",
            input_mode=request.input_mode,
            language_preference=request.language_preference,
            settings={
                "sensitivity_settings": {},
                "modules_to_complete": [request.module_id],
                "single_module_mode": True,
            },
        )
        session.add(interview_session)
        await session.flush()

        # Record consent if provided
        if request.consent:
            await self._record_consent(session, request.user_id, request.consent)

        # Initialize only this module
        modules = await self.module_state.initialize_modules(
            session,
            interview_session.id,
            [request.module_id],
        )

        # Get first question
        first_module = modules[0]
        first_question = self.question_bank.get_first_question(first_module.module_id)

        # Create first interviewer turn
        await self._create_interviewer_turn(
            session,
            interview_session.id,
            first_module.module_id,
            first_question,
            turn_index=0,
        )

        # Build response
        module_plan = self._build_module_plan(modules)
        bank = self.question_bank.load_question_bank(first_module.module_id)
        first_module_info = ModuleInfo(
            module_id=first_module.module_id,
            module_name=self.question_bank.get_module_name(first_module.module_id),
            estimated_duration_min=bank.estimated_duration_min,
            total_questions=len(bank.questions),
            status="active",
        )

        logger.info(f"Started single module {request.module_id} session {interview_session.id}")

        return InterviewStartResponse(
            session_id=interview_session.id,
            status="active",
            first_module=first_module_info,
            module_plan=module_plan,
            first_question=FirstQuestion(
                question_id=first_question.question_id,
                question_text=first_question.question_text,
                question_type=first_question.question_type,
                target_signal=first_question.target_signals[0]
                if first_question.target_signals
                else "",
                **_rich_fields_from_question(first_question, self.question_bank, first_module.module_id),
            ),
        )

    async def complete_module_and_exit(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
    ) -> ModuleCompleteResponse:
        """Save progress and exit to module selection.

        If module meets completion criteria, marks it as completed.
        Otherwise, pauses the session so the user can resume later.

        Args:
            session: Database session.
            interview_session_id: Interview session ID.

        Returns:
            ModuleCompleteResponse with completion status.
        """
        interview = await self._get_interview_session(session, interview_session_id)
        if not interview:
            raise ValueError("Interview session not found")

        # Get active module
        active_module = await self.module_state.get_active_module(
            session, interview_session_id
        )
        if not active_module:
            raise ValueError("No active module to complete")

        # Evaluate module completion
        completion = await self.module_state.evaluate_module_completion(
            session, interview_session_id, active_module.module_id
        )

        criteria = self.question_bank.get_module_completion_criteria(active_module.module_id)
        meets_criteria = (
            completion.is_complete
            or active_module.coverage_score >= criteria.coverage_threshold
        )

        if meets_criteria:
            # Module genuinely complete
            active_module.status = "completed"
            active_module.ended_at = datetime.now(timezone.utc)
            if completion.module_summary:
                active_module.completion_eval = {"summary": completion.module_summary}
            interview.status = "completed"
            interview.ended_at = datetime.now(timezone.utc)
            interview.total_duration_sec = int(
                (interview.ended_at - interview.started_at).total_seconds()
            )
            status = "module_completed"
            logger.info(f"Completed module {active_module.module_id} session {interview_session_id}")
        else:
            # Not enough coverage — pause so user can resume later
            active_module.status = "active"  # Keep active for resume
            interview.status = "paused"
            status = "module_paused"
            logger.info(
                f"Paused module {active_module.module_id} session {interview_session_id} "
                f"(coverage={active_module.coverage_score:.2f})"
            )

        await session.flush()

        # Check twin eligibility
        user_modules = await self.get_user_modules(session, interview.user_id)
        remaining = [m.module_id for m in user_modules.modules if m.status != "completed"]

        return ModuleCompleteResponse(
            session_id=interview_session_id,
            module_id=active_module.module_id,
            module_name=self.question_bank.get_module_name(active_module.module_id),
            status=status,
            module_summary=completion.module_summary if meets_criteria else None,
            coverage_score=active_module.coverage_score,
            confidence_score=active_module.confidence_score,
            can_generate_twin=user_modules.can_generate_twin,
            remaining_modules=remaining,
        )


# Singleton instance
_interview_service: InterviewService | None = None


def get_interview_service() -> InterviewService:
    """Get the singleton interview service instance."""
    global _interview_service
    if _interview_service is None:
        _interview_service = InterviewService()
    return _interview_service
