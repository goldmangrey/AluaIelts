from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class LexicalKind(StrEnum):
    WORD = "word"
    SYNONYM_UPGRADE = "synonym_upgrade"
    PHRASE = "phrase"
    COLLOCATION = "collocation"
    PHRASAL_VERB = "phrasal_verb"


class ReviewRating(StrEnum):
    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"


class ReviewSource(StrEnum):
    MIDDAY = "midday"
    EVENING = "evening"
    WEEKLY = "weekly"
    MANUAL = "manual"
    WIDGET = "widget"


class ReviewStatus(StrEnum):
    NEW = "new"
    LEARNING = "learning"
    REVIEW = "review"


class ReviewSessionKind(StrEnum):
    MIDDAY = "midday"
    EVENING = "evening"
    WEEKLY = "weekly"
    MANUAL = "manual"


class ReviewCardType(StrEnum):
    TERM_TO_MEANING = "term_to_meaning"
    MEANING_TO_TERM = "meaning_to_term"
    PHRASE_TO_MEANING = "phrase_to_meaning"
    CONTEXT_RECALL = "context_recall"


class LexicalItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    kind: LexicalKind
    term: str
    lemma: str | None = None
    translation_ru: str
    definition_en: str | None = None
    ipa: str | None = None
    usage_ru: str | None = None
    examples: tuple[str, ...] = Field(default=(), max_length=3)
    synonyms: tuple[str, ...] = ()
    source_tags: tuple[str, ...] = ()
    related_item_ids: tuple[str, ...] = ()
    related_ids: tuple[str, ...] = ()
    part_of_speech: str = "other"
    provenance: tuple[dict[str, object], ...] = ()
    cefr: str | None = None
    topic: str | None = None
    register: str | None = None


class DailyLexicalPack(BaseModel):
    model_config = ConfigDict(frozen=True)
    pack_id: str
    schema_version: int
    selection_algorithm_version: int
    generation_revision: int = 0
    user_id: str
    local_date: date
    timezone_at_generation: str
    content_version: str | int
    core_word_ids: tuple[str, ...]
    synonym_upgrade_ids: tuple[str, ...]
    phrase_ids: tuple[str, ...]
    created_at: datetime

    @property
    def all_item_ids(self) -> tuple[str, ...]:
        return self.core_word_ids + self.synonym_upgrade_ids + self.phrase_ids


class VocabularyReviewState(BaseModel):
    model_config = ConfigDict(frozen=True)
    schema_version: int
    user_id: str
    lexical_item_id: str
    status: ReviewStatus = ReviewStatus.NEW
    last_seen_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    next_due_at: datetime | None = None
    review_count: int = 0
    lapses: int = 0
    difficulty: float = Field(default=0.5, ge=0, le=1)
    interval_hours: float = 0
    last_rating: ReviewRating | None = None


class VocabularyReviewCard(BaseModel):
    model_config = ConfigDict(frozen=True)
    card_id: str
    lexical_item_id: str
    card_type: ReviewCardType
    item: LexicalItem


class VocabularyReviewSession(BaseModel):
    model_config = ConfigDict(frozen=True)
    session_id: str
    schema_version: int
    generation_version: int
    anchor_pack_ids: tuple[str, ...]
    content_version: str
    user_id: str
    local_date: date
    kind: ReviewSessionKind
    card_ids: tuple[str, ...]
    cards: tuple[VocabularyReviewCard, ...]
    created_at: datetime


class VocabularyReviewEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    event_id: str
    schema_version: int
    review_contract_version: int
    pack_id: str
    user_id: str
    session_id: str
    lexical_item_id: str
    rating: ReviewRating
    reviewed_at: datetime
    previous_due_at: datetime | None = None
    next_due_at: datetime
    source: ReviewSource
