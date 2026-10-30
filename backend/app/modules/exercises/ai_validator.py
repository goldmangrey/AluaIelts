import hashlib
import re

from app.modules.exercises.ai_models import AIExerciseCandidate, ExerciseGenerationSlot
from app.modules.exercises.models import (
    ExerciseGenerationSource,
    ExerciseInstance,
    ExerciseOption,
    ExerciseType,
)
from app.modules.exercises.prompts import PROMPT_VERSION


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split()).strip(" .!?\"'“”‘’")


def _clean(value: str) -> str:
    value = " ".join(value.split()).strip()
    if not value or any(ord(character) < 32 for character in value):
        raise ValueError("invalid_text")
    return value


class AIExerciseValidator:
    def build(
        self, slot: ExerciseGenerationSlot, candidate: AIExerciseCandidate, model: str
    ) -> ExerciseInstance | None:
        try:
            if candidate.slot_id != slot.slot_id or candidate.exercise_type != slot.exercise_type:
                return None
            if _normalize(candidate.proposed_answer) != _normalize(slot.canonical_answer_anchor):
                return None
            instruction = _clean(candidate.instruction)
            prompt = _clean(candidate.prompt)
            explanation = _clean(candidate.explanation)
            fallback = slot.fallback
            if self._contains_answer(instruction, slot.canonical_answer_anchor):
                return None
            if slot.exercise_type == ExerciseType.VOCABULARY_CONTEXT_GAP:
                prompt = self._context_gap(slot, candidate)
            elif slot.exercise_type == ExerciseType.VOCABULARY_RECALL:
                if self._contains_answer(prompt, slot.canonical_answer_anchor):
                    return None
            elif slot.exercise_type == ExerciseType.GRAMMAR_ERROR_CORRECTION:
                prompt = fallback.prompt
            elif self._contains_answer(prompt, slot.canonical_answer_anchor):
                return None

            options = fallback.options
            answer_key = fallback.answer_key
            if options:
                result = self._options(slot, candidate)
                if result is None:
                    return None
                options, answer_key = result
            return fallback.model_copy(
                update={
                    "instruction": instruction,
                    "prompt": prompt,
                    "options": options,
                    "answer_key": answer_key,
                    "explanation": explanation,
                    "generation_source": ExerciseGenerationSource.OPENAI,
                    "generation_model": model,
                    "generation_template_version": PROMPT_VERSION,
                }
            )
        except (ValueError, StopIteration):
            return None

    @staticmethod
    def _contains_answer(text: str, answer: str) -> bool:
        normalized_text = _normalize(text)
        normalized_answer = _normalize(answer)
        return bool(
            normalized_answer
            and re.search(rf"(?<!\w){re.escape(normalized_answer)}(?!\w)", normalized_text)
        )

    def _context_gap(self, slot: ExerciseGenerationSlot, candidate: AIExerciseCandidate) -> str:
        sentence = _clean(candidate.context_sentence or "")
        surface = _clean(candidate.target_surface_form or "")
        if _normalize(surface) != _normalize(slot.canonical_answer_anchor):
            raise ValueError("wrong_surface")
        pattern = re.compile(rf"(?<!\w){re.escape(surface)}(?!\w)", re.IGNORECASE)
        if len(pattern.findall(sentence)) != 1:
            raise ValueError("wrong_occurrence_count")
        return pattern.sub("___", sentence, count=1)

    def _options(
        self, slot: ExerciseGenerationSlot, candidate: AIExerciseCandidate
    ) -> tuple[tuple[ExerciseOption, ...], str] | None:
        correct = slot.canonical_answer_anchor
        distractors: list[str] = []
        for raw in candidate.distractors:
            value = _clean(raw)
            normalized = _normalize(value)
            normalized_correct = _normalize(correct)
            if (
                not normalized
                or normalized == normalized_correct
                or normalized in normalized_correct
                or normalized_correct in normalized
            ):
                continue
            if any(normalized == _normalize(existing) for existing in distractors):
                continue
            distractors.append(value)
        if not distractors:
            return None
        texts = [correct, *distractors][:4]
        if len(texts) < 2:
            return None
        exercise_id = slot.fallback.exercise_id
        texts.sort(key=lambda value: hashlib.sha256(f"{exercise_id}:{value}".encode()).hexdigest())
        options = tuple(
            ExerciseOption(id=chr(97 + index), text=value) for index, value in enumerate(texts)
        )
        answer_key = next(option.id for option in options if option.text == correct)
        return options, answer_key
