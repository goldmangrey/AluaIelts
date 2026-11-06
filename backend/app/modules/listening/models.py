from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base, JSONDocument


class ListeningAttemptRow(Base):
    __tablename__ = "listening_attempts"
    __table_args__ = (
        CheckConstraint("status IN ('in_progress','submitted')", name="ck_listening_status"),
        CheckConstraint("version >= 0", name="ck_listening_version"),
        Index("ix_listening_owner_started", "learner_id", "started_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learner_profiles.learner_id"))
    exam_id: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20))
    version: Mapped[int] = mapped_column(Integer, default=0)
    snapshot: Mapped[dict] = mapped_column(JSONDocument)
    answers: Mapped[dict] = mapped_column(JSONDocument, default=dict)
    state: Mapped[dict] = mapped_column(JSONDocument, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONDocument)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ListeningMutationRow(Base):
    __tablename__ = "listening_mutations"
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id"), primary_key=True
    )
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("listening_attempts.id"))
    mutation_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict] = mapped_column(JSONDocument)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ListeningGrantRow(Base):
    __tablename__ = "listening_playback_grants"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("listening_attempts.id"), index=True)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learner_profiles.learner_id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
