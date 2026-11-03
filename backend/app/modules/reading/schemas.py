from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateAttempt(StrictModel):
    event_id: UUID
    exam_id: str = Field(max_length=80)
    mode: Literal["full_exam", "passage_practice"]
    selected_passage: int | None = Field(default=None, ge=1, le=3)
    reuse_active: bool = False

    @model_validator(mode="after")
    def valid_selection(self):
        if (self.mode == "passage_practice") != (self.selected_passage is not None):
            raise ValueError("Select a passage only for passage_practice")
        return self


class AnswerMutation(StrictModel):
    event_id: UUID
    expected_version: int = Field(ge=0)
    answer: str = Field(max_length=500)


class BatchMutation(StrictModel):
    event_id: UUID
    expected_version: int = Field(ge=0)
    answers: dict[str, str] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def bound_answers(self):
        if any(len(k) > 100 or len(v) > 500 for k, v in self.answers.items()):
            raise ValueError("Answer too long")
        return self


class Annotation(StrictModel):
    id: UUID
    passage_id: str = Field(max_length=100)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    block_index: int = Field(ge=0)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    quote: str = Field(max_length=10000)
    color: Literal["yellow", "green", "blue", "pink"] = "yellow"
    note: str | None = Field(default=None, max_length=2000)


class CrossedOption(StrictModel):
    question_id: str = Field(max_length=100)
    option_label: str = Field(max_length=40)


class StateMutation(StrictModel):
    event_id: UUID
    expected_version: int = Field(ge=0)
    current_passage: int = Field(ge=1, le=3)
    # Complete replacement for annotation/strike-through lists; CAS prevents lost edits.
    annotations: list[Annotation] | None = Field(default=None, max_length=300)
    crossed_options: list[CrossedOption] | None = Field(default=None, max_length=300)


class SubmitMutation(StrictModel):
    event_id: UUID
    expected_version: int = Field(ge=0)


class CheckMutation(StrictModel):
    event_id: UUID
    expected_version: int = Field(ge=0)
    question_ids: list[str] = Field(min_length=1, max_length=40)
