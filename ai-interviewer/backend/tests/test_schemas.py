"""Tests for Pydantic schemas validation."""

import pytest
from uuid import uuid4

from app.schemas import (
    InterviewStartRequest,
    InterviewStartResponse,
    InterviewAnswerRequest,
    HealthResponse,
)


def test_interview_start_request_valid():
    """Test InterviewStartRequest with valid data."""
    request = InterviewStartRequest(
        user_id=uuid4(),
        input_mode="voice",
        language_preference="auto",
        modules_to_complete=["M1", "M2", "M3", "M4", "M5", "M6", "M7"],
    )
    assert request.input_mode == "voice"
    assert len(request.modules_to_complete) == 7


def test_interview_start_request_defaults():
    """Test InterviewStartRequest default values."""
    request = InterviewStartRequest(user_id=uuid4())
    assert request.input_mode == "text"
    assert request.language_preference == "auto"
    assert request.modules_to_complete == ["M1", "M2", "M3", "M4", "M5", "M6", "M7"]


def test_interview_answer_request_valid():
    """Test InterviewAnswerRequest with valid data."""
    request = InterviewAnswerRequest(
        answer_text="I work as a software engineer",
        question_id="M1_q01",
    )
    assert request.answer_text == "I work as a software engineer"


def test_health_response_valid():
    """Test HealthResponse with valid data."""
    from datetime import datetime, timezone

    response = HealthResponse(
        status="healthy",
        version="0.1.0",
        database="connected",
        timestamp=datetime.now(timezone.utc),
    )
    assert response.status == "healthy"
