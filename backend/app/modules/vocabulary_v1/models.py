from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base, JSONDocument


class VocabularyLearnedRow(Base):
    __tablename__ = "vocabulary_v1_learned"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[str] = mapped_column(String(180), primary_key=True)
    learned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    revision: Mapped[str] = mapped_column(String(36))


class VocabularyActionRow(Base):
    __tablename__ = "vocabulary_v1_actions"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), primary_key=True
    )
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSONDocument)


class VocabularyDayRow(Base):
    """Only the extended goal; never stores assigned card IDs."""

    __tablename__ = "vocabulary_v1_day_goals"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), primary_key=True
    )
    local_date: Mapped[date] = mapped_column(Date, primary_key=True)
    target: Mapped[int] = mapped_column(Integer)
