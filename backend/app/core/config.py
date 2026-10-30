from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_origins(value: Any) -> Any:
    if isinstance(value, str):
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    return value


def _parse_debug(value: Any) -> Any:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"debug", "development"}:
            return True
        if normalized in {"release", "production"}:
            return False
    return value


Origins = Annotated[list[str], BeforeValidator(_parse_origins)]
DebugFlag = Annotated[bool, BeforeValidator(_parse_debug)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default="Alua API", validation_alias="APP_NAME")
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")
    environment: Literal["local", "development", "staging", "production"] = Field(
        default="local", validation_alias="APP_ENV"
    )
    debug: DebugFlag = Field(default=False, validation_alias="DEBUG")
    api_prefix: str = Field(default="/api/v1", validation_alias="API_PREFIX")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_exercise_model: str = Field(
        default="gpt-5.6-luna", validation_alias="OPENAI_EXERCISE_MODEL"
    )
    openai_exercise_generation_enabled: bool = Field(
        default=True, validation_alias="OPENAI_EXERCISE_GENERATION_ENABLED"
    )
    openai_exercise_timeout_seconds: float = Field(
        default=20, ge=1, le=120, validation_alias="OPENAI_EXERCISE_TIMEOUT_SECONDS"
    )
    openai_exercise_max_retries: int = Field(
        default=1, ge=0, le=3, validation_alias="OPENAI_EXERCISE_MAX_RETRIES"
    )
    openai_exercise_max_output_tokens: int = Field(
        default=2500, ge=256, le=10000, validation_alias="OPENAI_EXERCISE_MAX_OUTPUT_TOKENS"
    )
    openai_analysis_model: str = Field(
        default="gpt-5.6-terra", validation_alias="OPENAI_ANALYSIS_MODEL"
    )
    openai_progress_analysis_enabled: bool = Field(
        default=True, validation_alias="OPENAI_PROGRESS_ANALYSIS_ENABLED"
    )
    openai_progress_timeout_seconds: float = Field(
        default=30, ge=1, le=120, validation_alias="OPENAI_PROGRESS_TIMEOUT_SECONDS"
    )
    openai_progress_max_retries: int = Field(
        default=1, ge=0, le=3, validation_alias="OPENAI_PROGRESS_MAX_RETRIES"
    )
    openai_progress_max_output_tokens: int = Field(
        default=3000, ge=256, le=10000, validation_alias="OPENAI_PROGRESS_MAX_OUTPUT_TOKENS"
    )
    openai_progress_chat_history_limit: int = Field(
        default=8, ge=1, le=20, validation_alias="OPENAI_PROGRESS_CHAT_HISTORY_LIMIT"
    )
    database_url: str = Field(
        default="postgresql+psycopg://alua@localhost/alua",
        validation_alias="DATABASE_URL",
    )
    database_pool_size: int = Field(default=5, ge=1, le=50, validation_alias="DB_POOL_SIZE")
    database_max_overflow: int = Field(default=10, ge=0, le=100, validation_alias="DB_MAX_OVERFLOW")
    enrollment_code_ttl_minutes: int = Field(
        default=30, ge=5, le=1440, validation_alias="ENROLLMENT_CODE_TTL_MINUTES"
    )
    allowed_origins: Origins = Field(default_factory=list, validation_alias="ALLOWED_ORIGINS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
