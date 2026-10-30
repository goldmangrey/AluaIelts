import time

import structlog
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from app.core.config import Settings
from app.integrations.openai.client import get_openai_client
from app.modules.exercises.ai_models import AIExerciseBatch, ExerciseGenerationBlueprint
from app.modules.exercises.prompts import SYSTEM_INSTRUCTIONS, build_generation_prompt

logger = structlog.get_logger(__name__)


class OpenAIExerciseGenerator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def available(self) -> bool:
        return bool(
            self._settings.openai_exercise_generation_enabled and self._settings.openai_api_key
        )

    def generate(self, blueprint: ExerciseGenerationBlueprint) -> AIExerciseBatch | None:
        if not self.available():
            return None
        started = time.monotonic()
        try:
            response = get_openai_client().responses.parse(
                model=self._settings.openai_exercise_model,
                instructions=SYSTEM_INSTRUCTIONS,
                input=build_generation_prompt(blueprint),
                text_format=AIExerciseBatch,
                max_output_tokens=self._settings.openai_exercise_max_output_tokens,
                store=False,
                timeout=self._settings.openai_exercise_timeout_seconds,
            )
            parsed = response.output_parsed
            if parsed is None:
                self._log_failure("refusal_or_incomplete", len(blueprint.slots), started)
            return parsed
        except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
            self._log_failure(type(exc).__name__, len(blueprint.slots), started)
        except APIStatusError as exc:
            self._log_failure(f"http_{exc.status_code}", len(blueprint.slots), started)
        except Exception as exc:  # SDK parsing/schema failures must never break practice.
            self._log_failure(type(exc).__name__, len(blueprint.slots), started)
        return None

    def _log_failure(self, reason: str, slots: int, started: float) -> None:
        logger.warning(
            "exercise_ai_generation_failed",
            reason=reason,
            model=self._settings.openai_exercise_model,
            slot_count=slots,
            fallback=True,
            latency_ms=round((time.monotonic() - started) * 1000),
        )
