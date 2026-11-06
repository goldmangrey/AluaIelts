from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateAttempt(Strict):
    event_id: UUID
    exam_id: str = Field(max_length=80)
    reuse_active: bool = True


class State(Strict):
    displayed_part: int = Field(1, ge=1, le=4)
    current_question: int = Field(1, ge=1, le=40)
    audio_part: int = Field(1, ge=1, le=4)
    playback_seconds: float = Field(0, ge=0, le=86400, allow_inf_nan=False)
    marked: list[int] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def marks(self):
        if any(n < 1 or n > 40 for n in self.marked) or len(set(self.marked)) != len(self.marked):
            raise ValueError("Invalid question marks")
        return self


class Mutation(Strict):
    event_id: UUID
    expected_version: int = Field(ge=0)


class Sync(Mutation):
    answers: dict[str, str] = Field(max_length=40)
    state: State

    @model_validator(mode="after")
    def bounded(self):
        if any(len(k) > 100 or len(v) > 500 for k, v in self.answers.items()):
            raise ValueError("Answer exceeds limits")
        return self
