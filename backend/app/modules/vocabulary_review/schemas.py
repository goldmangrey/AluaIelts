from datetime import date, time

from pydantic import BaseModel, Field

from app.modules.vocabulary_review.models import (
    LexicalItem,
    ReviewCardType,
    ReviewRating,
    ReviewSessionKind,
    VocabularyReviewState,
)


class LearningWindow(BaseModel):
    start: time = time(8)
    end: time = time(22)


class DailyPackResponse(BaseModel):
    pack_id: str
    schema_version: int
    selection_algorithm_version: int
    content_version: str
    core_words: tuple[LexicalItem, ...]
    synonym_upgrades: tuple[LexicalItem, ...]
    phrases: tuple[LexicalItem, ...]


class ReviewSessionSummary(BaseModel):
    session_id: str
    kind: ReviewSessionKind
    card_count: int
    completed_count: int = 0
    available_at: time


class CurrentRecall(BaseModel):
    session_id: str
    card_id: str
    lexical_item_id: str
    lexical_item: LexicalItem
    card_type: ReviewCardType
    prompt: str
    mode: str


class VocabularyLearningTodayResponse(BaseModel):
    local_date: date
    learning_window: LearningWindow
    daily_pack: DailyPackResponse
    review_due_count: int
    midday_session: ReviewSessionSummary
    evening_session: ReviewSessionSummary
    current_recall: CurrentRecall | None = None


class ReviewCardResponse(BaseModel):
    card_id: str
    lexical_item_id: str
    card_type: ReviewCardType
    front_term: str
    prompt: str
    item: LexicalItem


class VocabularyReviewSessionResponse(BaseModel):
    session_id: str
    schema_version: int
    generation_version: int
    pack_id: str
    content_version: str
    local_date: date
    kind: ReviewSessionKind
    cards: tuple[ReviewCardResponse, ...]
    completed_lexical_item_ids: tuple[str, ...]


class SubmitReviewResponseRequest(BaseModel):
    event_id: str = Field(min_length=8, max_length=100)
    lexical_item_id: str = Field(min_length=1, max_length=200)
    rating: ReviewRating


class SubmitReviewResponseResult(BaseModel):
    event_id: str
    state: VocabularyReviewState


class WeeklyReviewResponse(BaseModel):
    local_date: date
    session: ReviewSessionSummary
    week_item_count: int
    review_all_item_ids: tuple[str, ...]
