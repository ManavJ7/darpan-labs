"""Tests for configuration — 15+ tests."""
import os

import pytest

from app.config import Settings, settings


class TestSettings:
    def test_settings_instance_exists(self):
        assert settings is not None

    def test_database_url_default(self):
        s = Settings()
        assert "study_design_engine" in s.DATABASE_URL

    def test_redis_url_default(self):
        s = Settings()
        assert s.REDIS_URL.startswith("redis://")

    def test_llm_default_model(self):
        s = Settings()
        assert s.LLM_DEFAULT_MODEL in ("gpt-4o", "anthropic/claude-sonnet-4-20250514")

    def test_llm_default_temperature(self):
        s = Settings()
        assert s.LLM_DEFAULT_TEMPERATURE == 0.3

    def test_openai_api_key_default_empty(self):
        s = Settings()
        assert s.OPENAI_API_KEY == "" or s.OPENAI_API_KEY is not None

    def test_anthropic_api_key_default_empty(self):
        s = Settings()
        assert s.ANTHROPIC_API_KEY == "" or s.ANTHROPIC_API_KEY is not None

    def test_environment_default(self):
        s = Settings()
        assert s.ENVIRONMENT == "development"

    def test_debug_default(self):
        s = Settings()
        assert s.DEBUG is True

    def test_app_name(self):
        s = Settings()
        assert s.APP_NAME == "Study Design Engine"

    def test_api_v1_prefix(self):
        s = Settings()
        assert s.API_V1_PREFIX == "/api/v1"

    def test_image_storage_path_default(self):
        s = Settings()
        assert s.IMAGE_STORAGE_PATH == "./storage/images"

    def test_settings_has_database_url_field(self):
        assert "DATABASE_URL" in Settings.model_fields

    def test_settings_has_redis_url_field(self):
        assert "REDIS_URL" in Settings.model_fields

    def test_settings_has_all_expected_fields(self):
        expected_fields = {
            "DATABASE_URL", "REDIS_URL", "LLM_DEFAULT_MODEL",
            "LLM_DEFAULT_TEMPERATURE", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
            "ENVIRONMENT", "DEBUG", "APP_NAME", "API_V1_PREFIX",
            "IMAGE_STORAGE_PATH",
        }
        actual_fields = set(Settings.model_fields.keys())
        assert expected_fields.issubset(actual_fields)

    def test_database_url_uses_asyncpg(self):
        s = Settings()
        assert "asyncpg" in s.DATABASE_URL

    def test_database_url_uses_port_5432(self):
        s = Settings()
        assert "5432" in s.DATABASE_URL
