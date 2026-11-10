"""Existing backend providers keep their SDK contracts until authenticated migration."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.exceptions import ExternalServiceError
from app.modules.ai_progress import openai_provider as progress
from app.modules.ai_progress.models import AIProgressChatAnswer, AIProgressReport
from app.modules.exercises import ai_generator as exercises
from app.modules.exercises.ai_models import AIExerciseBatch


def settings(**overrides):
    return SimpleNamespace(
        **{
            "openai_progress_max_retries": 0,
            "openai_analysis_model": "legacy-progress-model",
            "openai_progress_max_output_tokens": 1000,
            "openai_progress_timeout_seconds": 20,
            "openai_exercise_generation_enabled": True,
            "openai_api_key": "synthetic-only",
            "openai_exercise_model": "legacy-exercise-model",
            "openai_exercise_max_output_tokens": 1000,
            "openai_exercise_timeout_seconds": 20,
            **overrides,
        }
    )


def sdk(monkeypatch, module, output):
    parse = Mock(return_value=SimpleNamespace(output_parsed=output))
    monkeypatch.setattr(
        module, "get_openai_client", lambda: SimpleNamespace(responses=SimpleNamespace(parse=parse))
    )
    return parse


@pytest.mark.parametrize(
    "method,output_type", [("report", AIProgressReport), ("chat", AIProgressChatAnswer)]
)
def test_progress_preserves_schema_timeout_and_no_store(monkeypatch, method, output_type):
    # SDK already validates output; this fixture checks the integration boundary.
    result = object()
    parse = sdk(monkeypatch, progress, result)
    assert getattr(progress.OpenAIProgressProvider(settings()), method)("synthetic") is result
    request = parse.call_args.kwargs
    assert request["text_format"] is output_type
    assert request["model"] == "legacy-progress-model"
    assert request["timeout"] == 20 and request["store"] is False


def test_progress_invalid_output_is_controlled(monkeypatch):
    sdk(monkeypatch, progress, None)
    with pytest.raises(ExternalServiceError) as error:
        progress.OpenAIProgressProvider(settings()).chat("synthetic")
    assert error.value.code == "ai_progress_invalid_response"


def test_exercise_preserves_schema_and_deterministic_fallback(monkeypatch):
    batch = AIExerciseBatch(exercises=[])
    parse = sdk(monkeypatch, exercises, batch)
    monkeypatch.setattr(exercises, "build_generation_prompt", lambda _: "synthetic")
    provider = exercises.OpenAIExerciseGenerator(settings())
    blueprint = SimpleNamespace(slots=["synthetic-slot"])
    assert provider.generate(blueprint) is batch
    assert parse.call_args.kwargs["text_format"] is AIExerciseBatch
    assert parse.call_args.kwargs["store"] is False
    parse.side_effect = RuntimeError("synthetic failure")
    assert provider.generate(blueprint) is None


def test_disabled_exercise_never_calls_ai(monkeypatch):
    parse = sdk(monkeypatch, exercises, None)
    assert (
        exercises.OpenAIExerciseGenerator(
            settings(openai_exercise_generation_enabled=False)
        ).generate(None)
        is None
    )
    parse.assert_not_called()
