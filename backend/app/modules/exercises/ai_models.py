from pydantic import BaseModel, ConfigDict, Field

from app.modules.exercises.models import ExerciseInstance, ExerciseType


class ExerciseGenerationSlot(BaseModel):
    """Server-owned canonical contract for one requested variation."""

    model_config = ConfigDict(frozen=True)

    slot_id: str
    exercise_type: ExerciseType
    content_type: str
    content_id: str
    curriculum_node_id: str | None
    cefr_level: str
    dimension: str
    evidence_kind: str
    difficulty: str
    canonical_answer_anchor: str
    canonical_facts: dict[str, object]
    allowed_source_material: tuple[str, ...]
    fallback: ExerciseInstance


class ExerciseGenerationBlueprint(BaseModel):
    model_config = ConfigDict(frozen=True)

    slots: tuple[ExerciseGenerationSlot, ...] = Field(min_length=1, max_length=8)


class AIExerciseCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot_id: str = Field(min_length=1, max_length=100)
    exercise_type: ExerciseType
    instruction: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=500)
    distractors: list[str] = Field(default_factory=list, max_length=3)
    proposed_answer: str = Field(min_length=1, max_length=250)
    explanation: str = Field(min_length=1, max_length=600)
    context_sentence: str | None = Field(default=None, max_length=500)
    target_surface_form: str | None = Field(default=None, max_length=250)


class AIExerciseBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exercises: list[AIExerciseCandidate] = Field(max_length=8)
