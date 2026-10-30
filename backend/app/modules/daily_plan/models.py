from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.student_model.models import CoverageStatus
from app.modules.users.models import EnglishLevel


class DailyPlanItemKind(StrEnum):
    GRAMMAR_FOCUS = "grammar_focus"
    VOCABULARY_LEARNING = "vocabulary_learning"
    GRAMMAR_REVIEW = "grammar_review"
    VOCABULARY_REVIEW = "vocabulary_review"
    REINFORCEMENT = "reinforcement"


class DailyPlanContentType(StrEnum):
    GRAMMAR_LESSON = "grammar_lesson"
    VOCABULARY_ITEM = "vocabulary_item"
    CURRICULUM_NODE = "curriculum_node"


class DailyPlanItemState(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class DailyPlanPriority(StrEnum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class DailyPlanReason(StrEnum):
    ACTIVE_CURRICULUM = "active_curriculum"
    NEXT_CURRICULUM = "next_curriculum"
    WEAK_MASTERY = "weak_mastery"
    DECLINING_MASTERY = "declining_mastery"
    REINFORCEMENT = "reinforcement"
    CONTINUITY = "continuity"


class DailyPlanStrategy(StrEnum):
    CURRICULUM_FIRST = "curriculum_first"
    BALANCED = "balanced"
    WEAKNESS_FOCUS = "weakness_focus"
    REVIEW_HEAVY = "review_heavy"


class DailyPlanStatus(StrEnum):
    READY = "ready"
    COMPLETED = "completed"
    NO_AVAILABLE_CONTENT = "no_available_content"


class DailyPlanItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    kind: DailyPlanItemKind
    content_type: DailyPlanContentType
    content_id: str
    curriculum_node_id: str | None = None
    title: str
    subtitle: str | None = None
    cefr_level: str | None = None
    estimated_minutes: int = Field(ge=1)
    priority: DailyPlanPriority
    reason: DailyPlanReason
    sequence: int = Field(ge=1)
    state: DailyPlanItemState = DailyPlanItemState.PENDING


class DailyPlanGenerationContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    declared_level: EnglishLevel | None = None
    recommended_stage_id: str | None = None
    active_node_id: str | None = None
    student_model_coverage: CoverageStatus
    target_minutes: int


class DailyPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_id: str
    schema_version: int = 2
    planner_version: int = 2
    user_id: str
    local_date: date
    timezone_at_generation: str
    target_minutes: int = Field(ge=5, le=240)
    estimated_minutes: int = Field(ge=0)
    curriculum_version: int = Field(ge=1)
    vocabulary_version: int = Field(ge=1)
    grammar_version: int = Field(ge=1)
    strategy: DailyPlanStrategy
    status: DailyPlanStatus
    items: tuple[DailyPlanItem, ...]
    archived_legacy_vocabulary_items: tuple[DailyPlanItem, ...] = ()
    created_at: datetime
    updated_at: datetime
    generation_context: DailyPlanGenerationContext

    @model_validator(mode="after")
    def validate_plan(self) -> "DailyPlan":
        if (self.schema_version, self.planner_version) not in {(1, 1), (2, 2)}:
            raise ValueError("Unsupported daily plan version.")
        if self.estimated_minutes != sum(item.estimated_minutes for item in self.items):
            raise ValueError("Plan estimate must equal its item estimates.")
        sequences = [item.sequence for item in self.items]
        if sequences != list(range(1, len(self.items) + 1)):
            raise ValueError("Daily plan sequences must be contiguous.")
        keys = [(item.content_type, item.content_id) for item in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError("Daily plan content must not be duplicated.")
        return self


class PlanningCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: DailyPlanItemKind
    content_type: DailyPlanContentType
    content_id: str
    curriculum_node_id: str | None = None
    title: str
    subtitle: str | None = None
    cefr_level: str | None = None
    reason: DailyPlanReason
    priority: DailyPlanPriority
    curriculum_order: int = 0
    progression_rank: int = 3
    review_rank: tuple[int, float, int, str] = (9, 1.0, 0, "")


class DailyPlanContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    uid: str
    local_date: date
    target_minutes: int = Field(ge=5, le=240)
    coverage: CoverageStatus
    progression_candidates: tuple[PlanningCandidate, ...]
    review_candidates: tuple[PlanningCandidate, ...]


class DailyPlanDraft(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: DailyPlanStrategy
    status: DailyPlanStatus
    items: tuple[DailyPlanItem, ...]
