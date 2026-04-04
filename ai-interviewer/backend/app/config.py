"""
Application configuration using pydantic-settings.
All settings are loaded from environment variables.
"""

from functools import lru_cache
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Darpan Labs Digital Twin"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # API
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001", "https://frontend-production-b8a9.up.railway.app"]

    # Database
    database_url: str = "postgresql+asyncpg://manavrsjain@localhost:5432/darpan"
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM Configuration
    llm_provider: str = "openai"  # openai, anthropic, etc.
    llm_model: str = "gpt-4-turbo-preview"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2000
    llm_max_retries: int = 3

    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # ASR/TTS
    deepgram_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None

    # Voice / ASR (OpenAI Whisper)
    whisper_model: str = "whisper-1"
    whisper_language: Optional[str] = None  # None = auto-detect

    # Observability
    sentry_dsn: Optional[str] = None
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # Auth
    auth_secret_key: str = "your-secret-key-change-in-production"
    auth_algorithm: str = "HS256"
    auth_access_token_expire_minutes: int = 1440  # 24 hours
    google_client_id: str = ""

    # Storage
    s3_bucket: Optional[str] = None
    s3_region: str = "us-east-1"
    audio_retention_days: int = 7

    # Twin pipeline
    twin_data_dir: str = str(
        __import__("pathlib").Path(__file__).parent.parent.parent.parent
        / "twin-generator" / "data"
    )

    @model_validator(mode="after")
    def ensure_asyncpg_driver(self):
        """Railway provides postgresql:// but we need postgresql+asyncpg://"""
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        return self

    @property
    def database_url_sync(self) -> str:
        """Return synchronous database URL (for Alembic)."""
        return self.database_url.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
