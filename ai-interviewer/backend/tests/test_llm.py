"""Tests for LLM abstraction layer."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pydantic import BaseModel

from app.llm.client import (
    LLMClient,
    LLMError,
    LLMValidationError,
    generate,
    get_llm_client,
)


class TestResponseSchema(BaseModel):
    """Test schema for LLM responses."""

    message: str
    confidence: float


@pytest.fixture
def llm_client():
    """Create LLM client for testing."""
    return LLMClient(max_retries=3)


def test_llm_client_initialization():
    """Test LLM client initializes with correct defaults."""
    client = LLMClient()
    assert client.max_retries == 3
    assert client.model is not None


def test_get_llm_client_returns_same_instance():
    """Test that get_llm_client returns singleton."""
    client1 = get_llm_client()
    client2 = get_llm_client()
    assert client1 is client2


@pytest.mark.asyncio
async def test_llm_client_generate_success(llm_client):
    """Test successful LLM generation."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"message": "Hello", "confidence": 0.9}'))
    ]

    with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
        result = await llm_client.generate(
            prompt="Test prompt",
            system="Test system",
        )
        assert "message" in result or "content" in result


@pytest.mark.asyncio
async def test_llm_client_generate_with_schema(llm_client):
    """Test LLM generation with response schema validation."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"message": "Hello", "confidence": 0.9}'))
    ]

    with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
        result = await llm_client.generate(
            prompt="Test prompt",
            response_format=TestResponseSchema,
        )
        assert isinstance(result, TestResponseSchema)
        assert result.message == "Hello"
        assert result.confidence == 0.9


@pytest.mark.asyncio
async def test_llm_client_retry_on_failure(llm_client):
    """Test that LLM client retries on failure."""
    call_count = 0

    async def mock_completion(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary error")
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"result": "success"}'))
        ]
        return mock_response

    with patch("litellm.acompletion", new_callable=AsyncMock, side_effect=mock_completion):
        result = await llm_client.generate(prompt="Test prompt")
        assert call_count == 3  # Should have retried


@pytest.mark.asyncio
async def test_llm_client_max_retries_exceeded(llm_client):
    """Test that LLM client raises error after max retries."""
    async def mock_completion(*args, **kwargs):
        raise Exception("Persistent error")

    with patch("litellm.acompletion", new_callable=AsyncMock, side_effect=mock_completion):
        with pytest.raises(LLMError):
            await llm_client.generate(prompt="Test prompt")


@pytest.mark.asyncio
async def test_llm_client_json_validation_error(llm_client):
    """Test that invalid JSON raises validation error."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="not valid json"))
    ]

    with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(LLMValidationError):
            await llm_client.generate(
                prompt="Test prompt",
                response_format=TestResponseSchema,
            )
