from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator

from app.modules.learning_events.models import LearningEvent, LearningEventType


class CreateLearningEventRequest(BaseModel):
    event_id: UUID
    schema_version: int = Field(default=1, ge=1)
    event_type: LearningEventType
    content_id: str = Field(min_length=1, max_length=200)
    curriculum_node_id: str | None = Field(default=None, min_length=1, max_length=200)
    client_occurred_at: datetime | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=100)
    session_id: UUID | None = None

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError("Only learning event schema version 1 is supported.")
        return value

    @field_validator("client_occurred_at")
    @classmethod
    def validate_client_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("client_occurred_at must include a timezone.")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("timezone must be a valid IANA timezone identifier.") from exc
        return value


class LearningEventsResponse(BaseModel):
    items: list[LearningEvent]
    limit: int
