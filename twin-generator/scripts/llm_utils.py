"""
Thin wrapper around LiteLLM for the twin generation pipeline.
Handles retries, JSON extraction, and concurrency limiting.
"""
import asyncio
import json
import re
import logging
from typing import Any

import litellm

from config.settings import (
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_CONCURRENT,
    API_KEY_POOL,
    DEEPSEEK_KEY_POOL,
    OPENAI_KEY_POOL,
)

logger = logging.getLogger(__name__)

# Semaphore to cap concurrent LLM calls (legacy / default)
_semaphore = asyncio.Semaphore(LLM_MAX_CONCURRENT)


class APIKeyPool:
    """Manages API keys for multiple providers with per-key concurrency limits."""

    def __init__(self, provider_keys: dict[str, list[str]], max_concurrent_per_key: int = 5):
        """
        provider_keys: {"anthropic": [key1, key2], "deepseek": [key1, key2, key3], "openai": [...]}
        """
        self._provider_keys: dict[str, list[str]] = {}
        self._provider_semaphores: dict[str, dict[str, asyncio.Semaphore]] = {}
        self._provider_assignments: dict[str, dict[str, str]] = {}  # provider -> {participant_id -> key}
        self._provider_next_idx: dict[str, int] = {}
        self._max_concurrent = max_concurrent_per_key

        for provider, keys in provider_keys.items():
            if not keys:
                continue
            self._provider_keys[provider] = keys
            self._provider_semaphores[provider] = {k: asyncio.Semaphore(max_concurrent_per_key) for k in keys}
            self._provider_assignments[provider] = {}
            self._provider_next_idx[provider] = 0

    @staticmethod
    def _detect_provider(model: str) -> str:
        """Extract provider from LiteLLM model string."""
        if "/" in model:
            return model.split("/")[0]
        if model.startswith("gpt-") or model.startswith("o1") or model.startswith("o3"):
            return "openai"
        if model.startswith("deepseek"):
            return "deepseek"
        if model.startswith("claude"):
            return "anthropic"
        return "anthropic"

    def assign(self, participant_id: str, model: str = "") -> str:
        """Get API key for participant+model combination."""
        provider = self._detect_provider(model) if model else "anthropic"
        if provider not in self._provider_keys:
            return ""  # let LiteLLM use env default
        assignments = self._provider_assignments[provider]
        if participant_id in assignments:
            return assignments[participant_id]
        keys = self._provider_keys[provider]
        idx = self._provider_next_idx[provider]
        key = keys[idx % len(keys)]
        assignments[participant_id] = key
        self._provider_next_idx[provider] = idx + 1
        return key

    def semaphore_for(self, participant_id: str, model: str = "") -> asyncio.Semaphore:
        """Get concurrency semaphore for participant's assigned key."""
        provider = self._detect_provider(model) if model else "anthropic"
        if provider not in self._provider_keys:
            return asyncio.Semaphore(self._max_concurrent)
        key = self.assign(participant_id, model)
        return self._provider_semaphores[provider][key]

    def key_for(self, participant_id: str, model: str = "") -> str:
        return self.assign(participant_id, model)


_api_key_pool = APIKeyPool({
    "anthropic": API_KEY_POOL,
    "deepseek": DEEPSEEK_KEY_POOL,
    "openai": OPENAI_KEY_POOL,
})


def extract_json(text: str) -> Any:
    """
    Robustly extract JSON from LLM output.
    Handles markdown code fences, trailing commas, and partial wrapping.
    """
    # Strip markdown code fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON object or array via brace/bracket matching
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == start_char:
                depth += 1
            elif text[i] == end_char:
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    # Remove trailing commas before closing braces/brackets
                    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    raise ValueError(f"Could not extract valid JSON from LLM response:\n{text[:500]}")


async def call_llm(
    prompt: str,
    system: str = "",
    max_tokens: int = 4096,
    temperature: float | None = None,
    model: str | None = None,
    expect_json: bool = True,
    participant_id: str = "default",
) -> Any:
    """
    Call the LLM with concurrency limiting and optional JSON extraction.

    Args:
        prompt: The user message content.
        system: Optional system message.
        max_tokens: Max tokens for response.
        temperature: Override default temperature.
        model: Override default model.
        expect_json: If True, parse response as JSON. If False, return raw text.
        participant_id: Route to a specific API key from the pool.

    Returns:
        Parsed JSON (dict/list) if expect_json=True, else raw string.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # Select semaphore and API key based on participant + model
    effective_model = model or LLM_MODEL
    sem = _api_key_pool.semaphore_for(participant_id, effective_model)
    api_key = _api_key_pool.key_for(participant_id, effective_model)

    max_retries = 5
    async with sem:
        for attempt in range(max_retries):
            try:
                effective = model or LLM_MODEL
                kwargs = dict(
                    model=effective,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature if temperature is not None else LLM_TEMPERATURE,
                )
                if api_key:
                    kwargs["api_key"] = api_key
                response = await litellm.acompletion(**kwargs)
                content = response.choices[0].message.content
                if expect_json:
                    return extract_json(content)
                return content
            except (json.JSONDecodeError, ValueError) as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"JSON parse failed (attempt {attempt + 1}/{max_retries}), retrying: {e}"
                    )
                    continue
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    # Exponential backoff: 5, 10, 20, 40s
                    wait = 5 * (2 ** attempt)
                    logger.warning(
                        f"LLM call failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait}s: {e}"
                    )
                    await asyncio.sleep(wait)
                    continue
                raise
