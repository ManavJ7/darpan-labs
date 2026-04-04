"""Module state tracking service (simplified)."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewModule, InterviewSession, InterviewTurn
from app.schemas.llm_responses import ModuleCompletionResult
from app.services.question_bank_service import (
    QuestionBankService,
    get_question_bank_service,
)

logger = logging.getLogger(__name__)


class ModuleStateService:
    """Track and update module state (coverage, confidence, signals)."""

    def __init__(
        self,
        question_bank: QuestionBankService | None = None,
    ):
        """Initialize module state service.

        Args:
            question_bank: Service for loading question banks.
        """
        self.question_bank = question_bank or get_question_bank_service()

    async def initialize_modules(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
        module_ids: list[str],
    ) -> list[InterviewModule]:
        """Create module records for a new session.

        Args:
            session: Database session.
            interview_session_id: Interview session ID.
            module_ids: List of module IDs to initialize.

        Returns:
            List of created InterviewModule records.
        """
        modules = []
        for i, module_id in enumerate(module_ids):
            status = "active" if i == 0 else "pending"
            started_at = datetime.now(timezone.utc) if i == 0 else None

            module = InterviewModule(
                session_id=interview_session_id,
                module_id=module_id,
                status=status,
                started_at=started_at,
                question_count=0,
                coverage_score=0.0,
                confidence_score=0.0,
                signals_captured=[],
            )
            session.add(module)
            modules.append(module)

        await session.flush()
        logger.info(
            f"Initialized {len(modules)} modules for session {interview_session_id}"
        )
        return modules

    async def get_module_state(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
        module_id: str,
    ) -> InterviewModule | None:
        """Get current state of a specific module.

        Args:
            session: Database session.
            interview_session_id: Interview session ID.
            module_id: Module ID to get.

        Returns:
            InterviewModule if found, None otherwise.
        """
        result = await session.execute(
            select(InterviewModule).where(
                InterviewModule.session_id == interview_session_id,
                InterviewModule.module_id == module_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_module(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
    ) -> InterviewModule | None:
        """Get the currently active module for a session.

        Args:
            session: Database session.
            interview_session_id: Interview session ID.

        Returns:
            Active InterviewModule if found, None otherwise.
        """
        result = await session.execute(
            select(InterviewModule).where(
                InterviewModule.session_id == interview_session_id,
                InterviewModule.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def get_all_modules(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
    ) -> list[InterviewModule]:
        """Get all modules for a session.

        Args:
            session: Database session.
            interview_session_id: Interview session ID.

        Returns:
            List of InterviewModule records.
        """
        result = await session.execute(
            select(InterviewModule)
            .where(InterviewModule.session_id == interview_session_id)
            .order_by(InterviewModule.module_id)
        )
        return list(result.scalars().all())

    async def update_module_after_answer(
        self,
        session: AsyncSession,
        module: InterviewModule,
    ) -> InterviewModule:
        """Update module state after receiving an answer.

        Simply increments the question count.

        Args:
            session: Database session.
            module: Module to update.

        Returns:
            Updated InterviewModule.
        """
        module.question_count += 1
        await session.flush()
        logger.info(
            f"Updated module {module.module_id}: question_count={module.question_count}"
        )
        return module

    async def evaluate_module_completion(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
        module_id: str,
    ) -> ModuleCompletionResult:
        """Evaluate if a module is complete.

        Complete = all bank questions have been asked (question_count >= total).

        Args:
            session: Database session.
            interview_session_id: Interview session ID.
            module_id: Module to evaluate.

        Returns:
            ModuleCompletionResult with completion status.
        """
        module = await self.get_module_state(session, interview_session_id, module_id)
        if not module:
            raise ValueError(f"Module {module_id} not found for session")

        bank = self.question_bank.load_question_bank(module_id)
        total_questions = len(bank.questions)
        is_complete = module.question_count >= total_questions

        return ModuleCompletionResult(
            is_complete=is_complete,
            coverage_score=1.0 if is_complete else module.question_count / max(total_questions, 1),
            confidence_score=1.0 if is_complete else 0.0,
            signals_captured=[],
            signals_missing=[],
            recommendation="COMPLETE" if is_complete else "ASK_MORE",
            module_summary=None,
        )

    async def transition_to_next_module(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
        current_module_id: str,
        module_summary: str | None = None,
    ) -> InterviewModule | None:
        """Mark current module complete and activate next.

        Args:
            session: Database session.
            interview_session_id: Interview session ID.
            current_module_id: Module to mark complete.
            module_summary: Optional summary of the completed module.

        Returns:
            Next InterviewModule if available, None if all complete.
        """
        # Get all modules
        modules = await self.get_all_modules(session, interview_session_id)

        # Find and update current module
        current_idx = None
        for i, m in enumerate(modules):
            if m.module_id == current_module_id:
                m.status = "completed"
                m.ended_at = datetime.now(timezone.utc)
                if module_summary:
                    m.completion_eval = {
                        **(m.completion_eval or {}),
                        "module_summary": module_summary,
                    }
                current_idx = i
                break

        if current_idx is None:
            raise ValueError(f"Module {current_module_id} not found")

        # Find next pending module
        for m in modules[current_idx + 1 :]:
            if m.status == "pending":
                m.status = "active"
                m.started_at = datetime.now(timezone.utc)
                await session.flush()
                logger.info(f"Transitioned to module {m.module_id}")
                return m

        # No more modules
        await session.flush()
        logger.info("All modules completed")
        return None

    async def get_completed_modules_summary(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
    ) -> str:
        """Get summary of all completed modules for cross-module context.

        Args:
            session: Database session.
            interview_session_id: Interview session ID.

        Returns:
            Formatted summary string.
        """
        modules = await self.get_all_modules(session, interview_session_id)
        completed = [m for m in modules if m.status == "completed"]

        if not completed:
            return "No modules completed yet."

        summaries = []
        for m in completed:
            eval_data = m.completion_eval or {}
            summary = eval_data.get("module_summary", "")
            signals = m.signals_captured or []
            summaries.append(
                f"{m.module_id} ({self.question_bank.get_module_name(m.module_id)}): "
                f"Signals: {', '.join(signals)}. {summary}"
            )

        return "\n".join(summaries)

    async def _get_module_turns(
        self,
        session: AsyncSession,
        interview_session_id: UUID,
        module_id: str,
    ) -> list[InterviewTurn]:
        """Get all turns for a specific module.

        Args:
            session: Database session.
            interview_session_id: Interview session ID.
            module_id: Module ID.

        Returns:
            List of InterviewTurn records.
        """
        result = await session.execute(
            select(InterviewTurn)
            .where(
                InterviewTurn.session_id == interview_session_id,
                InterviewTurn.module_id == module_id,
            )
            .order_by(InterviewTurn.turn_index)
        )
        return list(result.scalars().all())


# Singleton instance
_module_state_service: ModuleStateService | None = None


def get_module_state_service() -> ModuleStateService:
    """Get the singleton module state service instance."""
    global _module_state_service
    if _module_state_service is None:
        _module_state_service = ModuleStateService()
    return _module_state_service
