"""
LLM abstraction layer using LiteLLM.

Provides a thin wrapper around LiteLLM for:
- Model swapping via configuration
- Retry logic with exponential backoff
- JSON response validation
- Langfuse logging
"""

import asyncio
import json
import logging
from typing import Any, TypeVar

import litellm
from pydantic import BaseModel, ValidationError

from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.set_verbose = settings.debug

# Configure Langfuse if available
if settings.langfuse_public_key and settings.langfuse_secret_key:
    litellm.success_callback = ["langfuse"]
    litellm.failure_callback = ["langfuse"]


T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Base exception for LLM errors."""

    pass


class LLMResponseError(LLMError):
    """Error when LLM response is invalid."""

    pass


class LLMValidationError(LLMError):
    """Error when JSON validation fails."""

    pass


class LLMClient:
    """
    LLM client with retry logic and JSON validation.

    Usage:
        client = LLMClient()
        response = await client.generate(
            prompt="What is 2+2?",
            system="You are a helpful assistant.",
            temperature=0.7,
        )
    """

    def __init__(
        self,
        model: str | None = None,
        max_retries: int | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ):
        self.model = model or settings.llm_model
        self.max_retries = max_retries or settings.llm_max_retries
        self.temperature = temperature or settings.llm_temperature
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self.timeout = timeout if timeout is not None else 30.0

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: type[T] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | T:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user prompt to send
            system: Optional system message
            temperature: Override default temperature
            max_tokens: Override default max tokens
            response_format: Optional Pydantic model for JSON validation
            metadata: Optional metadata for logging

        Returns:
            Dict response or validated Pydantic model if response_format provided
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        for attempt in range(self.max_retries):
            try:
                coro = litellm.acompletion(
                    model=self.model,
                    messages=messages,
                    temperature=temperature or self.temperature,
                    max_tokens=max_tokens or self.max_tokens,
                    response_format=(
                        {"type": "json_object"} if response_format else None
                    ),
                    metadata=metadata or {},
                )
                if self.timeout:
                    response = await asyncio.wait_for(coro, timeout=self.timeout)
                else:
                    response = await coro

                content = response.choices[0].message.content
                if not content:
                    raise LLMResponseError("Empty response from LLM")

                # Parse JSON response
                if response_format:
                    try:
                        data = json.loads(content)
                        return response_format.model_validate(data)
                    except json.JSONDecodeError as e:
                        raise LLMValidationError(f"Invalid JSON response: {e}")
                    except ValidationError as e:
                        raise LLMValidationError(f"Response validation failed: {e}")

                # Try to parse as JSON even without schema
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {"content": content}

            except asyncio.TimeoutError:
                last_error = LLMError(f"LLM request timed out after {self.timeout}s")
                logger.warning(
                    f"LLM attempt {attempt + 1}/{self.max_retries} timed out"
                )
                if attempt < self.max_retries - 1:
                    delay = min(2 ** attempt * 0.5, 8.0)
                    await asyncio.sleep(delay)
                    continue
                raise LLMError(
                    f"LLM failed after {self.max_retries} attempts: timeout"
                )

            except (LLMValidationError, LLMResponseError) as e:
                last_error = e
                logger.warning(
                    f"LLM attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )
                if attempt < self.max_retries - 1:
                    delay = min(2 ** attempt * 0.5, 8.0)
                    await asyncio.sleep(delay)
                    continue
                raise

            except Exception as e:
                last_error = e
                logger.error(f"LLM error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    delay = min(2 ** attempt * 0.5, 8.0)
                    await asyncio.sleep(delay)
                    continue
                raise LLMError(f"LLM failed after {self.max_retries} attempts: {e}")

        raise LLMError(f"LLM failed after {self.max_retries} attempts: {last_error}")

    async def generate_with_schema(
        self,
        prompt: str,
        response_schema: type[T],
        system: str | None = None,
        temperature: float | None = None,
    ) -> T:
        """
        Generate a response and validate against a Pydantic schema.

        This is a convenience method that enforces JSON response format
        and validates against the provided schema.
        """
        result = await self.generate(
            prompt=prompt,
            system=system,
            temperature=temperature,
            response_format=response_schema,
        )
        return result  # type: ignore


# Default client instance
_default_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get the default LLM client instance."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


async def generate(
    prompt: str,
    system: str | None = None,
    temperature: float | None = None,
    response_format: type[T] | None = None,
    **kwargs: Any,
) -> dict[str, Any] | T:
    """
    Convenience function to generate LLM response.

    Usage:
        response = await generate(
            prompt="What is 2+2?",
            system="You are a helpful assistant.",
        )
    """
    client = get_llm_client()
    return await client.generate(
        prompt=prompt,
        system=system,
        temperature=temperature,
        response_format=response_format,
        **kwargs,
    )
