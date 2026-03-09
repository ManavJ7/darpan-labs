"""Interview API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.interview import (
    InterviewAnswerRequest,
    InterviewAnswerResponse,
    InterviewNextQuestionResponse,
    InterviewPauseResponse,
    InterviewSkipRequest,
    InterviewStartRequest,
    InterviewStartResponse,
    InterviewStatusResponse,
    ModuleCompleteResponse,
    StartSingleModuleRequest,
    UserModulesResponse,
)
from app.services.interview_service import InterviewService, get_interview_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interviews", tags=["Interviews"])


def get_service() -> InterviewService:
    """Dependency for interview service."""
    return get_interview_service()


@router.post(
    "/start",
    response_model=InterviewStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new interview session",
    description="""
    Start a new interview session for a user.

    Creates the session, initializes all requested modules (default: M1-M4),
    and returns the first question to ask.
    """,
)
async def start_interview(
    request: InterviewStartRequest,
    session: AsyncSession = Depends(get_session),
    service: InterviewService = Depends(get_service),
    current_user: User = Depends(get_current_user),
) -> InterviewStartResponse:
    """Start a new interview session."""
    try:
        request.user_id = current_user.id
        return await service.start_interview(session, request)
    except ValueError as e:
        logger.warning(f"Invalid interview start request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to start interview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start interview session",
        )


@router.post(
    "/{session_id}/answer",
    response_model=InterviewAnswerResponse,
    summary="Submit an answer",
    description="""
    Submit an answer to the current question.

    The answer is parsed using LLM to extract signals, assess specificity,
    and determine if a follow-up question is needed.
    """,
)
async def submit_answer(
    session_id: UUID,
    request: InterviewAnswerRequest,
    session: AsyncSession = Depends(get_session),
    service: InterviewService = Depends(get_service),
    current_user: User = Depends(get_current_user),
) -> InterviewAnswerResponse:
    """Submit an answer to the current question."""
    try:
        return await service.submit_answer(session, session_id, request)
    except ValueError as e:
        logger.warning(f"Invalid answer submission: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to submit answer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process answer",
        )


@router.post(
    "/{session_id}/next-question",
    response_model=InterviewNextQuestionResponse,
    summary="Get next question",
    description="""
    Get the next question for the interview.

    Uses adaptive questioning to select the best question based on:
    - Signals still needed for module completion
    - Previous answers and their quality
    - Follow-up needs from vague or contradictory answers

    Returns:
    - Next question if module continues
    - Module summary if module just completed
    - Completion status if all modules done
    """,
)
async def get_next_question(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
    service: InterviewService = Depends(get_service),
    current_user: User = Depends(get_current_user),
) -> InterviewNextQuestionResponse:
    """Get the next question for the interview."""
    try:
        return await service.get_next_question(session, session_id)
    except ValueError as e:
        logger.warning(f"Invalid next question request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to get next question: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate next question",
        )


@router.post(
    "/{session_id}/skip",
    response_model=InterviewNextQuestionResponse,
    summary="Skip current question",
    description="""
    Skip the current question and get the next one.

    The skip is recorded with an optional reason, and the next
    question is selected adaptively.
    """,
)
async def skip_question(
    session_id: UUID,
    request: InterviewSkipRequest = None,
    session: AsyncSession = Depends(get_session),
    service: InterviewService = Depends(get_service),
    current_user: User = Depends(get_current_user),
) -> InterviewNextQuestionResponse:
    """Skip current question and get next."""
    if request is None:
        request = InterviewSkipRequest()
    try:
        return await service.skip_question(session, session_id, request)
    except ValueError as e:
        logger.warning(f"Invalid skip request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to skip question: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to skip question",
        )


@router.post(
    "/{session_id}/pause",
    response_model=InterviewPauseResponse,
    summary="Pause interview",
    description="""
    Pause the interview for later resumption.

    The current state is saved and can be resumed using the
    resume endpoint.
    """,
)
async def pause_interview(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
    service: InterviewService = Depends(get_service),
    current_user: User = Depends(get_current_user),
) -> InterviewPauseResponse:
    """Pause interview for later resumption."""
    try:
        return await service.pause_interview(session, session_id)
    except ValueError as e:
        logger.warning(f"Invalid pause request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to pause interview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause interview",
        )


@router.post(
    "/{session_id}/resume",
    response_model=InterviewStartResponse,
    summary="Resume paused interview",
    description="""
    Resume a paused interview from the last position.

    Returns the current state including the last/current question
    that needs to be answered.
    """,
)
async def resume_interview(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
    service: InterviewService = Depends(get_service),
    current_user: User = Depends(get_current_user),
) -> InterviewStartResponse:
    """Resume paused interview from last position."""
    try:
        return await service.resume_interview(session, session_id)
    except ValueError as e:
        logger.warning(f"Invalid resume request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to resume interview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume interview",
        )


@router.get(
    "/{session_id}/status",
    response_model=InterviewStatusResponse,
    summary="Get interview status",
    description="""
    Get the full status of an interview session.

    Returns:
    - Session status (active, paused, completed)
    - All module progress with coverage and confidence scores
    - Current module and completed modules
    - Total duration
    """,
)
async def get_interview_status(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
    service: InterviewService = Depends(get_service),
    current_user: User = Depends(get_current_user),
) -> InterviewStatusResponse:
    """Get full interview status with module progress."""
    try:
        return await service.get_interview_status(session, session_id)
    except ValueError as e:
        logger.warning(f"Interview not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to get interview status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get interview status",
        )


@router.get(
    "/user/{user_id}/modules",
    response_model=UserModulesResponse,
    summary="Get user's module completion status",
    description="""
    Get the completion status of all modules for a user.

    Returns:
    - All 4 mandatory modules with their status (not_started, in_progress, completed)
    - Whether the user can generate a twin (all 4 modules complete)
    - Coverage and confidence scores for completed modules
    """,
)
async def get_user_modules(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    service: InterviewService = Depends(get_service),
    current_user: User = Depends(get_current_user),
) -> UserModulesResponse:
    """Get all module completion status for a user."""
    try:
        return await service.get_user_modules(session, current_user.id)
    except Exception as e:
        logger.error(f"Failed to get user modules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user modules",
        )


@router.post(
    "/start-module",
    response_model=InterviewStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a specific module",
    description="""
    Start a single module for a user.

    This allows users to complete one module at a time and exit.
    They can return later to complete other modules.
    """,
)
async def start_single_module(
    request: StartSingleModuleRequest,
    session: AsyncSession = Depends(get_session),
    service: InterviewService = Depends(get_service),
    current_user: User = Depends(get_current_user),
) -> InterviewStartResponse:
    """Start a specific module for a user."""
    try:
        request.user_id = current_user.id
        return await service.start_single_module(session, request)
    except ValueError as e:
        logger.warning(f"Invalid module start request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to start module: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start module",
        )


@router.post(
    "/{session_id}/complete-module",
    response_model=ModuleCompleteResponse,
    summary="Complete current module and exit",
    description="""
    Mark the current module as complete and return to module selection.

    Unlike the normal flow, this does NOT automatically start the next module.
    The user can return later to complete other modules.
    """,
)
async def complete_module_and_exit(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
    service: InterviewService = Depends(get_service),
    current_user: User = Depends(get_current_user),
) -> ModuleCompleteResponse:
    """Complete current module and exit to module selection."""
    try:
        return await service.complete_module_and_exit(session, session_id)
    except ValueError as e:
        logger.warning(f"Invalid complete module request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to complete module: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete module",
        )


