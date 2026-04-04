"""Tests for application configuration."""

import pytest
from unittest.mock import patch
import os

from app.config import Settings, get_settings, settings


class TestSettingsDefaults:
    """Tests for default configuration values."""

    def test_app_defaults(self):
        """Test application default settings."""
        s = Settings()
        assert s.app_name == "Darpan Labs Digital Twin"
        assert s.app_version == "0.1.0"
        assert s.debug is False
        assert s.environment == "development"

    def test_api_defaults(self):
        """Test API default settings."""
        s = Settings()
        assert s.api_prefix == "/api/v1"
        assert "http://localhost:3000" in s.cors_origins
        assert "http://127.0.0.1:3000" in s.cors_origins

    def test_database_defaults(self):
        """Test database default settings."""
        s = Settings()
        assert "postgresql+asyncpg" in s.database_url
        assert s.database_echo is False

    def test_redis_defaults(self):
        """Test Redis default settings."""
        s = Settings()
        assert "redis://localhost:6379" in s.redis_url

    def test_llm_defaults(self):
        """Test LLM default settings."""
        s = Settings()
        assert s.llm_provider == "openai"
        assert "gpt-4" in s.llm_model
        assert s.llm_temperature == 0.7
        assert s.llm_max_tokens == 2000
        assert s.llm_max_retries == 3

    def test_optional_api_keys_default_none(self):
        """Test that optional API keys default to None."""
        s = Settings()
        assert s.openai_api_key is None
        assert s.anthropic_api_key is None
        assert s.deepgram_api_key is None
        assert s.elevenlabs_api_key is None
        assert s.sentry_dsn is None
        assert s.langfuse_public_key is None
        assert s.langfuse_secret_key is None

    def test_auth_defaults(self):
        """Test authentication default settings."""
        s = Settings()
        assert s.auth_algorithm == "HS256"
        assert s.auth_access_token_expire_minutes == 30
        assert s.auth_secret_key is not None

    def test_whisper_defaults(self):
        """Test Whisper ASR default settings."""
        s = Settings()
        assert s.whisper_model == "whisper-1"
        assert s.whisper_language is None

    def test_storage_defaults(self):
        """Test storage default settings."""
        s = Settings()
        assert s.s3_bucket is None
        assert s.s3_region == "us-east-1"
        assert s.audio_retention_days == 7


class TestSettingsProperties:
    """Tests for computed properties."""

    def test_database_url_sync_property(self):
        """Test synchronous database URL conversion."""
        s = Settings()
        sync_url = s.database_url_sync
        assert "+asyncpg" not in sync_url
        assert "postgresql://" in sync_url


class TestSettingsSingleton:
    """Tests for settings singleton pattern."""

    def test_get_settings_returns_same_instance(self):
        """Test that get_settings returns cached instance."""
        # Note: This test verifies the caching behavior
        # The lru_cache ensures the same instance is returned
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_global_settings_instance_exists(self):
        """Test that global settings instance is available."""
        assert settings is not None
        assert isinstance(settings, Settings)


class TestSettingsEnvironmentOverrides:
    """Tests for environment variable overrides."""

    def test_settings_can_override_app_name(self):
        """Test that environment variables override defaults."""
        with patch.dict(os.environ, {"APP_NAME": "Custom App Name"}):
            s = Settings()
            assert s.app_name == "Custom App Name"

    def test_settings_can_override_debug(self):
        """Test debug flag override."""
        with patch.dict(os.environ, {"DEBUG": "true"}):
            s = Settings()
            assert s.debug is True

    def test_settings_can_override_environment(self):
        """Test environment override."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            s = Settings()
            assert s.environment == "production"

    def test_settings_can_override_llm_settings(self):
        """Test LLM settings override."""
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "anthropic",
            "LLM_MODEL": "claude-3-sonnet",
            "LLM_TEMPERATURE": "0.5",
            "LLM_MAX_TOKENS": "4000",
        }):
            s = Settings()
            assert s.llm_provider == "anthropic"
            assert s.llm_model == "claude-3-sonnet"
            assert s.llm_temperature == 0.5
            assert s.llm_max_tokens == 4000

    def test_settings_can_override_cors_origins(self):
        """Test CORS origins override."""
        with patch.dict(os.environ, {"CORS_ORIGINS": '["https://example.com"]'}):
            s = Settings()
            assert "https://example.com" in s.cors_origins


class TestSettingsValidation:
    """Tests for settings validation."""

    def test_settings_temperature_range(self):
        """Test that temperature can be set within valid range."""
        with patch.dict(os.environ, {"LLM_TEMPERATURE": "0.0"}):
            s = Settings()
            assert s.llm_temperature == 0.0

        with patch.dict(os.environ, {"LLM_TEMPERATURE": "1.0"}):
            s = Settings()
            assert s.llm_temperature == 1.0

    def test_settings_max_retries_positive(self):
        """Test max retries configuration."""
        with patch.dict(os.environ, {"LLM_MAX_RETRIES": "5"}):
            s = Settings()
            assert s.llm_max_retries == 5

    def test_settings_token_expire_minutes(self):
        """Test token expiration configuration."""
        with patch.dict(os.environ, {"AUTH_ACCESS_TOKEN_EXPIRE_MINUTES": "60"}):
            s = Settings()
            assert s.auth_access_token_expire_minutes == 60


class TestSettingsModelConfig:
    """Tests for pydantic-settings model configuration."""

    def test_settings_case_insensitive(self):
        """Test that settings are case insensitive."""
        # The model config specifies case_sensitive=False
        s = Settings()
        assert s.model_config.get("case_sensitive") is False

    def test_settings_extra_ignore(self):
        """Test that extra fields are ignored."""
        s = Settings()
        assert s.model_config.get("extra") == "ignore"

    def test_settings_env_file_encoding(self):
        """Test env file encoding configuration."""
        s = Settings()
        assert s.model_config.get("env_file_encoding") == "utf-8"
