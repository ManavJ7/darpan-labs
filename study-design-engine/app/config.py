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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
