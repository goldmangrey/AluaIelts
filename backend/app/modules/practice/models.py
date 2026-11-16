"""Only missing persistence: saved explanations, bounded avatars, Speaking completions."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base, JSONDocument


class SavedReviewRow(Base):
    __tablename__ = "practice_saved_reviews"
    __table_args__ = (
        UniqueConstraint("owner", "module", "attempt_id", "question_id", "input_hash"),
        Index("ix_saved_review_owner_attempt", "owner", "attempt_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner: Mapped[str] = mapped_column(ForeignKey("learner_profiles.learner_id"))
    module: Mapped[str] = mapped_column(String(16))
    attempt_id: Mapped[str] = mapped_column(String(36))
    question_id: Mapped[str] = mapped_column(String(100))
    input_hash: Mapped[str] = mapped_column(String(64))
    review_type: Mapped[str] = mapped_column(String(32), default="question_explanation")
    response: Mapped[dict] = mapped_column(JSONDocument)
    generation: Mapped[dict] = mapped_column(JSONDocument)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SpeakingAttemptRow(Base):
    __tablename__ = "speaking_attempts"
    __table_args__ = (
        UniqueConstraint("owner", "event_id"),
        Index("ix_speaking_owner_completed", "owner", "completed_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner: Mapped[str] = mapped_column(ForeignKey("learner_profiles.learner_id"))
    event_id: Mapped[str] = mapped_column(String(36))
    task_id: Mapped[str] = mapped_column(String(100))
    task_snapshot: Mapped[dict] = mapped_column(JSONDocument)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AvatarRow(Base):
    __tablename__ = "profile_avatars"
    owner: Mapped[str] = mapped_column(ForeignKey("learner_profiles.learner_id"), primary_key=True)
    data: Mapped[bytes] = mapped_column(LargeBinary)
    revision: Mapped[str] = mapped_column(String(36))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MistakeStateRow(Base):
    __tablename__ = "practice_mistake_states"
    owner: Mapped[str] = mapped_column(ForeignKey("learner_profiles.learner_id"), primary_key=True)
    module: Mapped[str] = mapped_column(String(16), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    item_key: Mapped[str] = mapped_column(String(150), primary_key=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
