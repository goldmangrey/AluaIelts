from datetime import datetime, timedelta

from app.modules.vocabulary_review.models import ReviewRating, ReviewStatus, VocabularyReviewState


class DeterministicVocabularyScheduler:
    """Readable deterministic SRS; ratings are scheduling signals, not mastery."""

    version = 2

    def apply(
        self, state: VocabularyReviewState, rating: ReviewRating, reviewed_at: datetime
    ) -> VocabularyReviewState:
        if rating == ReviewRating.AGAIN:
            interval, difficulty, lapses = 0.5, min(1.0, state.difficulty + 0.15), state.lapses + 1
            status = ReviewStatus.LEARNING
        elif rating == ReviewRating.HARD:
            interval = max(12, round(max(state.interval_hours, 8) * 1.5))
            difficulty, lapses, status = (
                min(1.0, state.difficulty + 0.05),
                state.lapses,
                ReviewStatus.LEARNING,
            )
        else:
            good_steps = (24, 72, 168, 336, 720, 1_440)
            interval = next(
                (step for step in good_steps if step > state.interval_hours),
                min(4_320, round(state.interval_hours * 1.5)),
            )
            difficulty, lapses, status = (
                max(0.0, state.difficulty - 0.08),
                state.lapses,
                ReviewStatus.REVIEW,
            )
        return state.model_copy(
            update={
                "status": status,
                "last_seen_at": reviewed_at,
                "last_reviewed_at": reviewed_at,
                "next_due_at": reviewed_at + timedelta(hours=interval),
                "review_count": state.review_count + 1,
                "lapses": lapses,
                "difficulty": difficulty,
                "interval_hours": interval,
                "last_rating": rating,
            }
        )
