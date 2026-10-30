from functools import lru_cache

from openai import OpenAI

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError


@lru_cache
def get_openai_client() -> OpenAI:
    settings = get_settings()
    api_key = settings.openai_api_key
    if not api_key:
        raise ExternalServiceError(
            message="OpenAI is not configured.", code="openai_not_configured"
        )
    return OpenAI(
        api_key=api_key,
        timeout=settings.openai_exercise_timeout_seconds,
        max_retries=settings.openai_exercise_max_retries,
    )
