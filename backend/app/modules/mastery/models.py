from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MasteryContentType(StrEnum):
    VOCABULARY_ITEM = "vocabulary_item"
    GRAMMAR_LESSON = "grammar_lesson"


class MasteryDimension(StrEnum):
    MEANING_RECOGNITION = "meaning_recognition"
    MEANING_RECALL = "meaning_recall"
    COLLOCATION = "collocation"
    CONTEXTUAL_USAGE = "contextual_usage"
    PRODUCTION = "production"
    RULE_RECOGNITION = "rule_recognition"
    FORM_CONTROL = "form_control"
    ERROR_DETECTION = "error_detection"
    CONTRAST_SELECTION = "contrast_selection"


VOCABULARY_DIMENSIONS = (
    MasteryDimension.MEANING_RECOGNITION,
    MasteryDimension.MEANING_RECALL,
    MasteryDimension.COLLOCATION,
    MasteryDimension.CONTEXTUAL_USAGE,
    MasteryDimension.PRODUCTION,
)
GRAMMAR_DIMENSIONS = (
    MasteryDimension.RULE_RECOGNITION,
    MasteryDimension.FORM_CONTROL,
    MasteryDimension.ERROR_DETECTION,
    MasteryDimension.CONTRAST_SELECTION,
    MasteryDimension.PRODUCTION,
)
DIMENSIONS_BY_CONTENT_TYPE = {
    MasteryContentType.VOCABULARY_ITEM: VOCABULARY_DIMENSIONS,
    MasteryContentType.GRAMMAR_LESSON: GRAMMAR_DIMENSIONS,
}


class MasteryLevel(StrEnum):
    UNASSESSED = "unassessed"
    DEVELOPING = "developing"
    COMPETENT = "competent"
    STRONG = "strong"


class MasteryTrend(StrEnum):
    UNKNOWN = "unknown"
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class EvidenceKind(StrEnum):
    RECOGNITION = "recognition"
    RECALL = "recall"
    CONTROLLED_USE = "controlled_use"
    ERROR_CORRECTION = "error_correction"
    CONTRAST = "contrast"
    PRODUCTION = "production"


class EvidenceDifficulty(StrEnum):
    EASY = "easy"
    STANDARD = "standard"
    HARD = "hard"


class MasteryEvidence(BaseModel):
    """Internal trusted input. It is deliberately not exposed as an HTTP schema."""

    model_config = ConfigDict(frozen=True)

    event_id: UUID
    content_type: MasteryContentType
    content_id: str = Field(min_length=1, max_length=200)
    dimension: MasteryDimension
    outcome: float = Field(ge=0.0, le=1.0)
    occurred_at: datetime
    evidence_kind: EvidenceKind
    difficulty: EvidenceDifficulty = EvidenceDifficulty.STANDARD
    error_tags: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_evidence(self) -> "MasteryEvidence":
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must include a timezone.")
        if self.dimension not in DIMENSIONS_BY_CONTENT_TYPE[self.content_type]:
            raise ValueError("Dimension is not valid for this content type.")
        return self


class MasteryState(BaseModel):
    model_config = ConfigDict(frozen=True)

    state_id: str
    user_id: str
    content_type: MasteryContentType
    content_id: str
    dimension: MasteryDimension
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_count: int = Field(ge=0)
    successful_evidence_count: int = Field(ge=0)
    failed_evidence_count: int = Field(ge=0)
    weighted_success_sum: float = Field(ge=0.0)
    weighted_evidence_sum: float = Field(ge=0.0)
    previous_score: float | None = Field(default=None, ge=0.0, le=1.0)
    last_evidence_at: datetime
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    level: MasteryLevel
    trend: MasteryTrend
    error_tag_counts: dict[str, int] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    engine_version: int = 1

    @model_validator(mode="after")
    def validate_assessment_state(self) -> "MasteryState":
        if self.evidence_count == 0 and self.score is not None:
            raise ValueError("An unassessed state cannot have a score.")
        if self.evidence_count > 0 and self.score is None:
            raise ValueError("An assessed state must have a score.")
        return self


def make_state_id(
    content_type: MasteryContentType,
    content_id: str,
    dimension: MasteryDimension,
) -> str:
    return f"{content_type.value}__{content_id}__{dimension.value}"
