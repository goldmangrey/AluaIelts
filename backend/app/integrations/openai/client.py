from functools import lru_cache

from openai import OpenAI

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError


@lru_cache
def get_openai_client() -> OpenAI:
    api_key = get_settings().openai_api_key
    if not api_key:
        raise ExternalServiceError(
            message="OpenAI is not configured.", code="openai_not_configured"
        )
    return OpenAI(api_key=api_key)
