from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.modules.mastery.models import (
    MasteryContentType,
    MasteryDimension,
    MasteryLevel,
)
from app.modules.users.models import EnglishLevel


class CoverageStatus(StrEnum):
    INSUFFICIENT = "insufficient"
    PARTIAL = "partial"
    MEANINGFUL = "meaningful"


class StudentModelCurriculum(BaseModel):
    declared_level: EnglishLevel | None = None
    recommended_stage_id: str | None = None
    recommended_stage_title: str | None = None
    active_node_id: str | None = None


class StudentModelMasteryOverview(BaseModel):
    assessed_skill_count: int = 0
    vocabulary_assessed_item_count: int = 0
    grammar_assessed_lesson_count: int = 0
    vocabulary_level: MasteryLevel = MasteryLevel.UNASSESSED
    grammar_level: MasteryLevel = MasteryLevel.UNASSESSED


class StudentModelStrength(BaseModel):
    content_type: MasteryContentType
    content_id: str
    dimension: MasteryDimension
    level: MasteryLevel
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)


class StudentModelWeakness(BaseModel):
    content_type: MasteryContentType
    content_id: str
    dimension: MasteryDimension
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)


class StudentModelErrorTag(BaseModel):
    tag: str
    count: int = Field(ge=1)


class StudentModelDataQuality(BaseModel):
    assessment_evidence_count: int = 0
    assessed_vocabulary_items: int = 0
    assessed_grammar_lessons: int = 0
    coverage_status: CoverageStatus = CoverageStatus.INSUFFICIENT


class StudentModelSnapshot(BaseModel):
    user_id: str
    generated_at: datetime
    curriculum: StudentModelCurriculum
    mastery: StudentModelMasteryOverview
    strengths: list[StudentModelStrength] = Field(default_factory=list)
    weaknesses: list[StudentModelWeakness] = Field(default_factory=list)
    recent_error_tags: list[StudentModelErrorTag] = Field(default_factory=list)
    data_quality: StudentModelDataQuality
