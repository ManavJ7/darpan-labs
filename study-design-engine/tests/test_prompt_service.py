"""Tests for PromptService — 7+ tests."""
import os
import tempfile

import pytest

from app.services.prompt_service import PromptService, get_prompt_service


class TestPromptService:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        # Create a test prompt file
        with open(os.path.join(self.tmpdir, "test_template.txt"), "w") as f:
            f.write("Hello {name}, your study is about {topic}.")
        self.service = PromptService(prompts_dir=self.tmpdir)

    def test_load_template_success(self):
        content = self.service.load_template("test_template")
        assert "Hello" in content
        assert "{name}" in content

    def test_format_prompt_with_kwargs(self):
        result = self.service.format_prompt("test_template", name="Alice", topic="FMCG")
        assert result == "Hello Alice, your study is about FMCG."

    def test_missing_template_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            self.service.load_template("nonexistent_template")

    def test_template_caching(self):
        # Load once
        self.service.load_template("test_template")
        assert "test_template" in self.service._cache

        # Load again — should come from cache
        content = self.service.load_template("test_template")
        assert "Hello" in content

    def test_clear_cache(self):
        self.service.load_template("test_template")
        assert len(self.service._cache) > 0
        self.service.clear_cache()
        assert len(self.service._cache) == 0

    def test_format_prompt_with_missing_kwarg_raises(self):
        with pytest.raises(KeyError):
            self.service.format_prompt("test_template", name="Alice")
            # missing 'topic' kwarg


class TestGetPromptService:
    def test_get_prompt_service_returns_instance(self):
        import app.services.prompt_service as module
        module._prompt_service = None
        service = get_prompt_service()
        assert isinstance(service, PromptService)

    def test_get_prompt_service_singleton(self):
        import app.services.prompt_service as module
        module._prompt_service = None
        s1 = get_prompt_service()
        s2 = get_prompt_service()
        assert s1 is s2
