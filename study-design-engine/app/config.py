from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:darpan@localhost:5432/study_design_engine"
    REDIS_URL: str = "redis://localhost:6379/1"
    LLM_DEFAULT_MODEL: str = "gpt-4o"
    LLM_DEFAULT_TEMPERATURE: float = 0.3
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "Study Design Engine"
    API_V1_PREFIX: str = "/api/v1"
    IMAGE_STORAGE_PATH: str = "./storage/images"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
