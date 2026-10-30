import re
import unicodedata

from app.core.exceptions import ValidationError
from app.modules.exercises.models import ExerciseInstance


def normalize_answer(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).replace("’", "'").replace("‘", "'")
    normalized = re.sub(r"\s+", " ", normalized.strip().casefold())
    # Unambiguous contractions only; do not expand 's or 'd without context.
    for short, full in {
        "don't": "do not",
        "doesn't": "does not",
        "didn't": "did not",
        "isn't": "is not",
        "aren't": "are not",
        "wasn't": "was not",
        "weren't": "were not",
        "can't": "cannot",
        "won't": "will not",
        "haven't": "have not",
        "hasn't": "has not",
        "hadn't": "had not",
        "wouldn't": "would not",
        "shouldn't": "should not",
    }.items():
        normalized = re.sub(r"\b" + re.escape(short) + r"\b", full, normalized)
    return normalized.rstrip(".!?").strip()


class ExerciseGrader:
    def grade(self, exercise: ExerciseInstance, answer: str) -> bool:
        if not answer.strip():
            raise ValidationError(message="Answer cannot be empty.", code="exercise_invalid_answer")
        if exercise.options:
            if answer not in {option.id for option in exercise.options}:
                raise ValidationError(
                    message="The selected option is invalid.", code="exercise_invalid_answer"
                )
            return answer == exercise.answer_key
        return normalize_answer(answer) in {
            normalize_answer(value) for value in (exercise.answer_key, *exercise.accepted_answers)
        }
