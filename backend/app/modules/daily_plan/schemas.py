from datetime import date, datetime

from pydantic import BaseModel, Field

from app.modules.daily_plan.models import (
    DailyPlanContentType,
    DailyPlanGenerationContext,
    DailyPlanItemKind,
    DailyPlanItemState,
    DailyPlanPriority,
    DailyPlanReason,
    DailyPlanStatus,
    DailyPlanStrategy,
)


class EnsureDailyPlanRequest(BaseModel):
    timezone: str = Field(min_length=1, max_length=100)


class DailyPlanItemResponse(BaseModel):
    item_id: str
    kind: DailyPlanItemKind
    content_type: DailyPlanContentType
    content_id: str
    curriculum_node_id: str | None
    title: str
    subtitle: str | None = None
    cefr_level: str | None = None
    estimated_minutes: int
    priority: DailyPlanPriority
    reason: DailyPlanReason
    state: DailyPlanItemState
    sequence: int


class DailyPlanVocabularySummary(BaseModel):
    pack_id: str
    content_version: str
    total_lexical_units: int
    core_word_count: int
    synonym_upgrade_count: int
    phrase_chunk_count: int
    review_due_count: int


class DailyPlanResponse(BaseModel):
    plan_id: str
    schema_version: int
    planner_version: int
    local_date: date
    timezone_at_generation: str
    target_minutes: int
    estimated_minutes: int
    curriculum_version: int
    vocabulary_version: int
    grammar_version: int
    strategy: DailyPlanStrategy
    status: DailyPlanStatus
    items: list[DailyPlanItemResponse]
    vocabulary: DailyPlanVocabularySummary
    total_items: int
    completed_items: int
    remaining_items: int
    completed_estimated_minutes: int
    created_at: datetime
    updated_at: datetime
    generation_context: DailyPlanGenerationContext
