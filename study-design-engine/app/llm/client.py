import json
import logging
import os
import re
import time

from tenacity import retry, stop_after_attempt, retry_if_exception_type

from app.config import settings

# litellm reads API keys from os.environ, not from pydantic settings
if settings.OPENAI_API_KEY and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
if settings.ANTHROPIC_API_KEY and not os.environ.get("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling common issues."""
    text = text.strip()

    # Strip markdown code fences
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # First, try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find the outermost JSON object with brace matching
    start = text.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", text, 0)

    depth = 0
    in_string = False
    escape_next = False
    end = start

    for i in range(start, len(text)):
        ch = text[i]
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    candidate = text[start : end + 1]

    # Try parsing the extracted object
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Fix common issues: trailing commas before } or ]
    fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        # Log the problematic content for debugging
        logger.error(
            "Failed to parse JSON from LLM response (len=%d). "
            "Error at position %d: %s. Last 200 chars: %s",
            len(candidate),
            e.pos,
            e.msg,
            candidate[-200:] if len(candidate) > 200 else candidate,
        )
        raise


class LLMClient:
    """LiteLLM-based client for LLM interactions."""

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
    ):
        self.model = model or settings.LLM_DEFAULT_MODEL
        self.temperature = temperature if temperature is not None else settings.LLM_DEFAULT_TEMPERATURE

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int = 16000,
    ) -> str:
        """Generate text from a prompt using LiteLLM."""
        import litellm

        use_model = model or self.model
        use_temp = temperature if temperature is not None else self.temperature

        start_time = time.time()
        response = await litellm.acompletion(
            model=use_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=use_temp,
            max_completion_tokens=max_tokens,
        )
        latency = time.time() - start_time

        result = response.choices[0].message.content
        usage = response.usage

        logger.info(
            "LLM call: model=%s, tokens_in=%s, tokens_out=%s, latency=%.2fs",
            use_model,
            usage.prompt_tokens if usage else "?",
            usage.completion_tokens if usage else "?",
            latency,
        )

        return result

    async def generate_json(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int = 16000,
    ) -> dict:
        """Generate JSON from a prompt, with retry on parse failure."""
        return await self._generate_json_with_retry(prompt, model, temperature, max_tokens)

    @retry(
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(json.JSONDecodeError),
    )
    async def _generate_json_with_retry(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int = 16000,
    ) -> dict:
        raw = await self.generate(prompt, model, temperature, max_tokens)
        return _extract_json(raw)


_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Dependency function to get LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
