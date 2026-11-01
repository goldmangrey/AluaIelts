"""Only Reading-owned tables; existing learning tables are untouched."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base, JSONDocument


class ReadingAttemptRow(Base):
    __tablename__ = "reading_attempts"
    __table_args__ = (
        CheckConstraint("mode IN ('full_exam', 'passage_practice')", name="ck_reading_mode"),
        CheckConstraint(
            "status IN ('in_progress', 'submitted', 'expired')", name="ck_reading_status"
        ),
        CheckConstraint("version >= 0", name="ck_reading_version"),
        CheckConstraint(
            "(mode = 'full_exam' AND selected_passage IS NULL AND deadline_at IS NOT NULL)"
            " OR (mode = 'passage_practice' AND selected_passage BETWEEN 1 AND 3"
            " AND deadline_at IS NULL)",
            name="ck_reading_selection",
        ),
        Index("ix_reading_learner_started", "learner_id", "started_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learner_profiles.learner_id"))
    exam_id: Mapped[str] = mapped_column(String(80))
    dataset_version: Mapped[str] = mapped_column(String(40))
    content_hash: Mapped[str] = mapped_column(String(64))
    content_revision: Mapped[str] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(24))
    selected_passage: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    version: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Immutable exam/key snapshots preserve historical grading even when canonical files change.
    snapshot: Mapped[dict] = mapped_column(JSONDocument)
    answers: Mapped[dict] = mapped_column(JSONDocument, default=dict)
    state: Mapped[dict] = mapped_column(JSONDocument, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONDocument)


class ReadingMutationRow(Base):
    __tablename__ = "reading_mutations"
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id"), primary_key=True
    )
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("reading_attempts.id"), index=True)
    mutation_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict] = mapped_column(JSONDocument)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
