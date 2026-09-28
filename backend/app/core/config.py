from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import AliasChoices, BeforeValidator, Field
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
    openai_analysis_model: str = Field(
        default="gpt-5.6-terra", validation_alias="OPENAI_ANALYSIS_MODEL"
    )
    firebase_project_id: str | None = Field(default=None, validation_alias="FIREBASE_PROJECT_ID")
    google_application_credentials: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "GOOGLE_APPLICATION_CREDENTIALS",
            "FIREBASE_CREDENTIALS_PATH",
        ),
    )
    allowed_origins: Origins = Field(default_factory=list, validation_alias="ALLOWED_ORIGINS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
