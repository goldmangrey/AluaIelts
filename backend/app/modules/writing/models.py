from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base, JSONDocument


class WritingTaskRow(Base):
    __tablename__ = "writing_tasks"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSONDocument)


class WritingAttemptRow(Base):
    __tablename__ = "writing_attempts"
    __table_args__ = (UniqueConstraint("owner", "event_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner: Mapped[str] = mapped_column(ForeignKey("learner_profiles.learner_id"), index=True)
    event_id: Mapped[str] = mapped_column(String(36))
    task_id: Mapped[str] = mapped_column(ForeignKey("writing_tasks.id"), index=True)
    task_snapshot: Mapped[dict] = mapped_column(JSONDocument)
    version: Mapped[int] = mapped_column(Integer, default=0)
    essay: Mapped[str] = mapped_column(Text, default="")
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    assessment: Mapped[dict | None] = mapped_column(JSONDocument, nullable=True)
    ai_status: Mapped[str] = mapped_column(String(24), default="idle")
    ai_lease: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ai_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_calls: Mapped[int] = mapped_column(Integer, default=0)
