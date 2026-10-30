from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.mastery.models import (
    MasteryContentType,
    MasteryDimension,
    MasteryLevel,
    MasteryState,
    MasteryTrend,
)


class MasteryStatesResponse(BaseModel):
    items: list[MasteryState]
    limit: int
    offset: int


class MasteryDimensionSummary(BaseModel):
    dimension: MasteryDimension
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    level: MasteryLevel = MasteryLevel.UNASSESSED
    trend: MasteryTrend = MasteryTrend.UNKNOWN
    evidence_count: int = 0
    last_evidence_at: datetime | None = None


class ErrorTagCount(BaseModel):
    tag: str
    count: int


class ContentMasterySummary(BaseModel):
    content_type: MasteryContentType
    content_id: str
    overall_score: float | None = Field(default=None, ge=0.0, le=1.0)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_level: MasteryLevel = MasteryLevel.UNASSESSED
    dimensions: list[MasteryDimensionSummary]
    evidence_count: int = 0
    last_evidence_at: datetime | None = None
    top_error_tags: list[ErrorTagCount] = Field(default_factory=list)
