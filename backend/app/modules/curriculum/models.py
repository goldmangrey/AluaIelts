from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.modules.users.models import EnglishLevel


class CurriculumTrack(StrEnum):
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    MIXED = "mixed"


class CurriculumNodeType(StrEnum):
    GRAMMAR_TOPIC = "grammar_topic"
    VOCABULARY_TRACK = "vocabulary_track"
    REINFORCEMENT = "reinforcement"


class CurriculumNodeStatus(StrEnum):
    LOCKED = "locked"
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"


class CurriculumNode(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    stage_id: str
    track: CurriculumTrack
    type: CurriculumNodeType
    title: str
    short_title: str | None = None
    description: str = "Academic curriculum topic."
    order: int = Field(ge=1)
    cefr_level: EnglishLevel
    estimated_minutes: int = Field(default=30, ge=5, le=240)
    prerequisites: tuple[str, ...] = ()
    objectives: tuple[str, ...] = ()
    content_refs: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    required: bool = True


class CurriculumStage(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    order: int = Field(ge=1)
    title: str
    subtitle: str
    cefr_from: EnglishLevel
    cefr_to: EnglishLevel
    description: str
    target_ielts_range: str | None = None
    estimated_weeks: int | None = Field(default=None, ge=1)
    nodes: tuple[CurriculumNode, ...]


class CurriculumProgram(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int = Field(ge=1)
    version_label: str
    title: str
    description: str
    stages: tuple[CurriculumStage, ...]


class UserCurriculumState(BaseModel):
    program_id: str
    curriculum_version: int
    recommended_stage_id: str
    active_node_id: str | None = None
    started_node_ids: list[str] = Field(default_factory=list)
    completed_node_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CurriculumNodeProgress(BaseModel):
    node: CurriculumNode
    status: CurriculumNodeStatus
    is_recommended: bool = False


class CurriculumStageProgress(BaseModel):
    stage: CurriculumStage
    nodes: list[CurriculumNodeProgress]


class UserCurriculumOverview(BaseModel):
    program_id: str
    curriculum_version: int
    version_label: str
    recommended_stage_id: str
    active_node_id: str | None
    state: UserCurriculumState
    stages: list[CurriculumStageProgress]
    recommended_next_nodes: list[CurriculumNode]
