from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.daily_plan.models import DailyPlanContentType, DailyPlanItemKind
from app.modules.mastery.models import EvidenceDifficulty, EvidenceKind, MasteryDimension


class ExerciseType(StrEnum):
    VOCABULARY_MEANING_MCQ = "vocabulary_meaning_mcq"
    VOCABULARY_RECALL = "vocabulary_recall"
    VOCABULARY_COLLOCATION_MCQ = "vocabulary_collocation_mcq"
    VOCABULARY_CONTEXT_GAP = "vocabulary_context_gap"
    GRAMMAR_RULE_MCQ = "grammar_rule_mcq"
    GRAMMAR_FORM_CHOICE = "grammar_form_choice"
    GRAMMAR_ERROR_CORRECTION = "grammar_error_correction"
    GRAMMAR_CONTRAST_MCQ = "grammar_contrast_mcq"


class ExerciseSessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"


class ExerciseGenerationSource(StrEnum):
    DETERMINISTIC = "deterministic"
    OPENAI = "openai"


class ExerciseGenerationMode(StrEnum):
    DETERMINISTIC = "deterministic"
    OPENAI = "openai"
    HYBRID = "hybrid"


class ExerciseOption(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    text: str


class ExerciseInstance(BaseModel):
    model_config = ConfigDict(frozen=True)
    exercise_id: str
    exercise_type: ExerciseType
    content_type: DailyPlanContentType
    content_id: str
    curriculum_node_id: str | None = None
    dimension: MasteryDimension
    evidence_kind: EvidenceKind
    difficulty: EvidenceDifficulty = EvidenceDifficulty.STANDARD
    instruction: str
    prompt: str
    options: tuple[ExerciseOption, ...] = ()
    accepted_answers: tuple[str, ...] = ()
    answer_key: str
    correct_answer_display: str
    explanation: str
    error_tags: tuple[str, ...] = ()
    sequence: int = Field(ge=1)
    generation_source: ExerciseGenerationSource = ExerciseGenerationSource.DETERMINISTIC
    generation_model: str | None = None
    generation_template_version: str | None = None


class ExerciseSession(BaseModel):
    model_config = ConfigDict(frozen=True)
    session_id: str
    schema_version: int = 1
    engine_version: int = 1
    user_id: str
    daily_plan_date: date
    daily_plan_item_id: str
    content_type: DailyPlanContentType
    content_id: str
    curriculum_node_id: str | None = None
    plan_item_kind: DailyPlanItemKind
    status: ExerciseSessionStatus = ExerciseSessionStatus.ACTIVE
    exercises: tuple[ExerciseInstance, ...]
    created_at: datetime
    updated_at: datetime
    total_exercises: int = Field(ge=1)
    answered_exercises: int = Field(default=0, ge=0)
    correct_exercises: int = Field(default=0, ge=0)
    curriculum_version: int = Field(ge=1)
    vocabulary_version: int = Field(ge=1)
    grammar_version: int = Field(ge=1)
    generation_mode: ExerciseGenerationMode = ExerciseGenerationMode.DETERMINISTIC
    openai_model: str | None = None
    prompt_version: str | None = None

    @model_validator(mode="after")
    def validate_session(self) -> "ExerciseSession":
        if self.schema_version != 1 or self.engine_version != 1:
            raise ValueError("Unsupported exercise session version.")
        if self.total_exercises != len(self.exercises):
            raise ValueError("Exercise total does not match session content.")
        if self.answered_exercises > self.total_exercises:
            raise ValueError("Answered count exceeds exercise total.")
        return self


class ExerciseAttempt(BaseModel):
    model_config = ConfigDict(frozen=True)
    attempt_id: UUID
    exercise_id: str
    session_id: str
    topic_id: str | None = None
    answer_status: str | None = None
    exercise_type: ExerciseType | None = None
    submitted_answer: str
    is_correct: bool
    outcome: float = Field(ge=0.0, le=1.0)
    client_occurred_at: datetime | None = None
    server_received_at: datetime
    response_time_ms: int | None = Field(default=None, ge=0, le=1_800_000)
