from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LearningEventType(StrEnum):
    CURRICULUM_NODE_STARTED = "curriculum_node_started"
    GRAMMAR_LESSON_OPENED = "grammar_lesson_opened"
    VOCABULARY_TRACK_OPENED = "vocabulary_track_opened"
    VOCABULARY_ITEM_OPENED = "vocabulary_item_opened"
    EXERCISE_ANSWERED = "exercise_answered"


class LearningEventCategory(StrEnum):
    ENGAGEMENT = "engagement"
    ASSESSMENT = "assessment"
    REVIEW = "review"
    SYSTEM = "system"


class LearningEventSource(StrEnum):
    IOS_APP = "ios_app"
    BACKEND = "backend"
    WIDGET = "widget"


class LearningContentType(StrEnum):
    CURRICULUM_NODE = "curriculum_node"
    GRAMMAR_LESSON = "grammar_lesson"
    VOCABULARY_TRACK = "vocabulary_track"
    VOCABULARY_ITEM = "vocabulary_item"


EVENT_CONTENT_TYPES: dict[LearningEventType, LearningContentType] = {
    LearningEventType.CURRICULUM_NODE_STARTED: LearningContentType.CURRICULUM_NODE,
    LearningEventType.GRAMMAR_LESSON_OPENED: LearningContentType.GRAMMAR_LESSON,
    LearningEventType.VOCABULARY_TRACK_OPENED: LearningContentType.VOCABULARY_TRACK,
    LearningEventType.VOCABULARY_ITEM_OPENED: LearningContentType.VOCABULARY_ITEM,
}


class AssessmentEventPayload(BaseModel):
    exercise_id: str
    exercise_session_id: str
    daily_plan_item_id: str
    exercise_type: str
    dimension: str
    evidence_kind: str
    difficulty: str
    outcome: float = Field(ge=0.0, le=1.0)
    is_correct: bool
    response_time_ms: int | None = None
    error_tags: tuple[str, ...] = ()


class LearningEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: UUID
    schema_version: int = Field(default=1, ge=1)
    user_id: str = Field(min_length=1)
    event_type: LearningEventType
    category: LearningEventCategory
    source: LearningEventSource
    content_type: LearningContentType
    content_id: str = Field(min_length=1, max_length=200)
    curriculum_node_id: str | None = Field(default=None, min_length=1, max_length=200)
    client_occurred_at: datetime | None = None
    server_received_at: datetime
    timezone: str | None = Field(default=None, min_length=1, max_length=100)
    session_id: UUID | None = None
    assessment: AssessmentEventPayload | None = None

    @model_validator(mode="after")
    def validate_event_shape(self) -> "LearningEvent":
        if self.schema_version not in {1, 2}:
            raise ValueError("Unsupported learning event schema version.")
        if self.event_type == LearningEventType.EXERCISE_ANSWERED:
            if (
                self.schema_version != 2
                or self.source != LearningEventSource.BACKEND
                or not self.assessment
            ):
                raise ValueError("Assessment events must be trusted schema version 2 events.")
            if self.content_type not in {
                LearningContentType.GRAMMAR_LESSON,
                LearningContentType.VOCABULARY_ITEM,
            }:
                raise ValueError("Assessment target content is invalid.")
        elif EVENT_CONTENT_TYPES[self.event_type] != self.content_type:
            raise ValueError("Event type and content type do not match.")
        if self.client_occurred_at and self.client_occurred_at.tzinfo is None:
            raise ValueError("client_occurred_at must include a timezone.")
        if self.server_received_at.tzinfo is None:
            raise ValueError("server_received_at must include a timezone.")
        return self

    def idempotency_payload(self) -> dict[str, object]:
        return self.model_dump(exclude={"server_received_at"}, mode="json")
