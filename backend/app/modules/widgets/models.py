from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class WidgetUserMode(StrEnum):
    LEARNER = "learner"
    PARTNER = "partner"
    BOTH = "both"


class WidgetTodaySnapshot(BaseModel):
    completed_items: int = 0
    total_items: int = 0
    estimated_planned_minutes: int = 0
    estimated_completed_minutes: int = 0
    current_focus: str | None = None
    grammar_items: int = 0
    vocabulary_items: int = 0
    review_items: int = 0


class WidgetVocabularySnapshot(BaseModel):
    content_id: str
    term: str
    translation_ru: str
    ipa: str | None = None
    cefr: str | None = None
    definition_en: str | None = None
    example: str | None = None
    part_of_speech: str | None = None


class WidgetGrammarSnapshot(BaseModel):
    content_id: str
    display_title: str
    short_title: str
    formula: str
    support_ru: str | None = None
    example: str | None = None


class WidgetPracticeSnapshot(BaseModel):
    local_date: date
    daily_plan_item_id: str
    title: str
    item_kind: str
    existing_session_id: str | None = None
    question_count: int | None = None
    remaining_count: int | None = None
    estimated_minutes: int
    has_existing_session: bool = False


class LearnerWidgetSnapshot(BaseModel):
    display_name: str | None = None
    local_date: date
    pack_id: str
    content_version: str
    pack_schema_version: int
    today: WidgetTodaySnapshot | None = None
    vocabulary_cards: tuple[WidgetVocabularySnapshot, ...] = ()
    grammar_cards: tuple[WidgetGrammarSnapshot, ...] = ()
    practice: WidgetPracticeSnapshot | None = None


class PartnerWidgetPermissions(BaseModel):
    daily_activity: bool
    progress_analytics: bool


class PartnerWidgetSnapshot(BaseModel):
    learner_display_name: str
    local_date: date
    active_today: bool | None = None
    completed_items: int | None = None
    total_items: int | None = None
    estimated_planned_minutes: int | None = None
    estimated_completed_minutes: int | None = None
    current_focus: str | None = None
    active_days_7: int | None = None
    last_activity_at: datetime | None = None
    permissions: PartnerWidgetPermissions


class WidgetSnapshotEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)
    schema_version: int = Field(default=5, ge=5, le=5)
    generation_id: str
    generated_at: datetime
    valid_from: datetime
    valid_until: datetime
    user_mode: WidgetUserMode
    learner: LearnerWidgetSnapshot | None = None
    partner: PartnerWidgetSnapshot | None = None
