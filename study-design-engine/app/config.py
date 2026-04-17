from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://manavrsjain@localhost:5432/darpan"
    REDIS_URL: str = "redis://localhost:6379/0"
    LLM_DEFAULT_MODEL: str = "gpt-4o"
    LLM_DEFAULT_TEMPERATURE: float = 0.3
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "Study Design Engine"
    API_V1_PREFIX: str = "/api/v1"
    IMAGE_STORAGE_PATH: str = "./storage/images"
    GOOGLE_CLIENT_ID: str = ""
    JWT_SECRET_KEY: str = "darpan-sde-dev-secret-change-in-prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 72
    # Comma-separated list of emails allowed to sign in. Empty = allow all
    # (development default). In production, set this to the beta invite list.
    ALLOWED_EMAILS: str = ""
    # Comma-separated list of frontend origins allowed by CORS. Replaces the
    # previous wildcard which was incompatible with allow_credentials=True.
    CORS_ORIGINS: str = "http://localhost:3099,http://localhost:3001,http://localhost:3000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        """Force the async driver prefix regardless of how the URL is supplied.

        Railway's Postgres add-on emits `postgres://` (historical Heroku format);
        SQLAlchemy async needs `postgresql+asyncpg://`. Rewrite at load time so
        the app + Alembic both work without the operator remembering to hand-edit
        the connection string.
        """
        if not v:
            return v
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://") :]
        if v.startswith("postgresql://") and "+asyncpg" not in v:
            return "postgresql+asyncpg://" + v[len("postgresql://") :]
        return v

    @property
    def allowed_emails_set(self) -> set[str]:
        """Return the lower-cased allowlist as a set. Empty set = allow all."""
        return {e.strip().lower() for e in self.ALLOWED_EMAILS.split(",") if e.strip()}

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
