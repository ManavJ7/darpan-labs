"""Tests for LLM client — 12+ tests."""
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.llm.client import LLMClient, get_llm_client


class TestLLMClient:
    def test_instantiation_defaults(self):
        client = LLMClient()
        assert client.model in ("gpt-4o", "anthropic/claude-sonnet-4-20250514")
        assert client.temperature == 0.3

    def test_instantiation_custom(self):
        client = LLMClient(model="claude-3-opus", temperature=0.7)
        assert client.model == "claude-3-opus"
        assert client.temperature == 0.7

    def test_has_generate_method(self):
        client = LLMClient()
        assert hasattr(client, "generate")
        assert callable(client.generate)

    def test_has_generate_json_method(self):
        client = LLMClient()
        assert hasattr(client, "generate_json")
        assert callable(client.generate_json)

    @pytest.mark.asyncio
    async def test_generate_calls_litellm(self):
        client = LLMClient()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
            result = await client.generate("Test prompt")
            assert result == "Hello"

    @pytest.mark.asyncio
    async def test_generate_json_parses_json(self):
        client = LLMClient()
        expected = {"key": "value"}
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(expected)
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
            result = await client.generate_json("Test prompt")
            assert result == expected

    @pytest.mark.asyncio
    async def test_generate_json_strips_markdown_code_block(self):
        client = LLMClient()
        expected = {"key": "value"}
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = f"```json\n{json.dumps(expected)}\n```"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
            result = await client.generate_json("Test prompt")
            assert result == expected

    @pytest.mark.asyncio
    async def test_generate_uses_custom_model(self):
        client = LLMClient()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response) as mock_acomp:
            await client.generate("Test", model="gpt-3.5-turbo")
            call_kwargs = mock_acomp.call_args
            assert call_kwargs.kwargs["model"] == "gpt-3.5-turbo"

    @pytest.mark.asyncio
    async def test_generate_uses_custom_temperature(self):
        client = LLMClient()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response) as mock_acomp:
            await client.generate("Test", temperature=0.9)
            call_kwargs = mock_acomp.call_args
            assert call_kwargs.kwargs["temperature"] == 0.9


class TestGetLLMClient:
    def test_get_llm_client_returns_instance(self):
        import app.llm.client as module
        module._llm_client = None
        client = get_llm_client()
        assert isinstance(client, LLMClient)

    def test_get_llm_client_returns_same_instance(self):
        import app.llm.client as module
        module._llm_client = None
        client1 = get_llm_client()
        client2 = get_llm_client()
        assert client1 is client2
