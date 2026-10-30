from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.modules.daily_plan.models import DailyPlanContentType, DailyPlanItemKind
from app.modules.exercises.models import ExerciseOption, ExerciseSessionStatus, ExerciseType


class ExerciseItemState(StrEnum):
    UNANSWERED = "unanswered"
    ANSWERED = "answered"


class CreateExerciseSessionRequest(BaseModel):
    local_date: date
    daily_plan_item_id: str = Field(min_length=1, max_length=200)


class SubmitExerciseAttemptRequest(BaseModel):
    attempt_id: UUID
    unknown: bool = False
    selected_option_id: str | None = Field(default=None, min_length=1, max_length=20)
    text_answer: str | None = Field(default=None, min_length=1, max_length=500)
    client_occurred_at: datetime | None = None
    response_time_ms: int | None = Field(default=None, ge=0, le=1_800_000)

    @model_validator(mode="after")
    def validate_answer(self) -> "SubmitExerciseAttemptRequest":
        if self.unknown:
            if self.selected_option_id is not None or self.text_answer is not None:
                raise ValueError("Unknown cannot include an answer.")
        elif (self.selected_option_id is None) == (self.text_answer is None):
            raise ValueError("Provide exactly one answer type.")
        if self.client_occurred_at and self.client_occurred_at.tzinfo is None:
            raise ValueError("client_occurred_at must include a timezone.")
        return self

    @property
    def answer(self) -> str:
        return "__unknown__" if self.unknown else self.selected_option_id or self.text_answer or ""


class ExerciseAttemptFeedback(BaseModel):
    attempt_id: UUID
    exercise_id: str
    is_correct: bool
    outcome: float
    correct_answer_display: str
    explanation: str
    error_tags: list[str]


class ExercisePublicResponse(BaseModel):
    exercise_id: str
    exercise_type: ExerciseType
    content_type: DailyPlanContentType
    content_id: str
    curriculum_node_id: str | None
    instruction: str
    prompt: str
    options: list[ExerciseOption]
    sequence: int
    state: ExerciseItemState
    result: ExerciseAttemptFeedback | None = None


class ExerciseSessionProgress(BaseModel):
    answered: int
    total: int
    correct: int


class ExerciseSessionResponse(BaseModel):
    session_id: str
    schema_version: int
    engine_version: int
    daily_plan_date: date
    daily_plan_item_id: str
    content_type: DailyPlanContentType
    content_id: str
    curriculum_node_id: str | None
    plan_item_kind: DailyPlanItemKind
    status: ExerciseSessionStatus
    exercises: list[ExercisePublicResponse]
    progress: ExerciseSessionProgress
    created_at: datetime
    updated_at: datetime


class ExerciseAttemptResult(ExerciseAttemptFeedback):
    session_progress: ExerciseSessionProgress
    session_status: ExerciseSessionStatus
    daily_plan_item_completed: bool
