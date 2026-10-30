import time
from typing import TypeVar

import structlog
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError
from pydantic import BaseModel

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError
from app.integrations.openai.client import get_openai_client
from app.modules.ai_progress.models import AIProgressChatAnswer, AIProgressReport
from app.modules.ai_progress.prompts import SYSTEM_INSTRUCTIONS

logger = structlog.get_logger(__name__)
OutputT = TypeVar("OutputT", bound=BaseModel)


class OpenAIProgressProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def report(self, prompt: str) -> AIProgressReport:
        return self._parse(prompt, AIProgressReport)

    def chat(self, prompt: str) -> AIProgressChatAnswer:
        return self._parse(prompt, AIProgressChatAnswer)

    def _parse(self, prompt: str, output_type: type[OutputT]) -> OutputT:
        started = time.monotonic()
        attempts = self._settings.openai_progress_max_retries + 1
        for attempt in range(attempts):
            try:
                response = get_openai_client().responses.parse(
                    model=self._settings.openai_analysis_model,
                    instructions=SYSTEM_INSTRUCTIONS,
                    input=prompt,
                    text_format=output_type,
                    max_output_tokens=self._settings.openai_progress_max_output_tokens,
                    store=False,
                    timeout=self._settings.openai_progress_timeout_seconds,
                )
                parsed = response.output_parsed
                if parsed is None:
                    raise ExternalServiceError(
                        message="AI analysis is temporarily unavailable.",
                        code="ai_progress_invalid_response",
                    )
                logger.info(
                    "ai_progress_response_completed",
                    model=self._settings.openai_analysis_model,
                    output_type=output_type.__name__,
                    latency_ms=round((time.monotonic() - started) * 1000),
                )
                return parsed
            except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
                if attempt + 1 >= attempts:
                    self._raise_provider_error(exc, started)
            except APIStatusError as exc:
                if exc.status_code < 500 or attempt + 1 >= attempts:
                    self._raise_provider_error(exc, started)
            except ExternalServiceError as exc:
                if exc.code == "ai_progress_invalid_response":
                    raise
                self._raise_provider_error(exc, started)
            except Exception as exc:
                self._raise_provider_error(exc, started)
        raise AssertionError("OpenAI retry loop did not return or raise")

    def _raise_provider_error(self, exc: Exception, started: float) -> None:
        logger.warning(
            "ai_progress_response_failed",
            reason=type(exc).__name__,
            model=self._settings.openai_analysis_model,
            latency_ms=round((time.monotonic() - started) * 1000),
        )
        raise ExternalServiceError(
            message=(
                "AI analysis is temporarily unavailable. "
                "Your progress dashboard is still available."
            ),
            code="ai_progress_temporarily_unavailable",
        ) from exc
