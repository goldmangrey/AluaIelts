from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON

JSONDocument = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


class LearnerProfileRow(Base):
    __tablename__ = "learner_profiles"
    learner_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    legacy_identity_key: Mapped[str | None] = mapped_column(String(128), unique=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class EnrollmentCodeRow(Base):
    __tablename__ = "enrollment_codes"
    code_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    learner_id: Mapped[str | None] = mapped_column(ForeignKey("learner_profiles.learner_id"))


class DeviceEnrollmentRow(Base):
    __tablename__ = "device_enrollments"
    enrollment_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    device_name: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class DailyPlanRow(Base):
    __tablename__ = "daily_plans"
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), primary_key=True
    )
    local_date: Mapped[date] = mapped_column(Date, primary_key=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class VocabularyPackRow(Base):
    __tablename__ = "vocabulary_packs"
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), primary_key=True
    )
    pack_id: Mapped[str] = mapped_column(String(180), primary_key=True)
    local_date: Mapped[date] = mapped_column(Date, index=True)
    schema_version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class ReviewSessionRow(Base):
    __tablename__ = "review_sessions"
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), primary_key=True
    )
    session_id: Mapped[str] = mapped_column(String(180), primary_key=True)
    session_type: Mapped[str] = mapped_column(String(40), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class CanonicalVocabularyStateRow(Base):
    __tablename__ = "canonical_vocabulary_states"
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), primary_key=True
    )
    lexical_item_id: Mapped[str] = mapped_column(String(180), primary_key=True)
    review_count: Mapped[int] = mapped_column(Integer)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    schema_version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class ReviewResponseRow(Base):
    __tablename__ = "review_responses"
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), primary_key=True
    )
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(180), index=True)
    lexical_item_id: Mapped[str] = mapped_column(String(180), index=True)
    rating: Mapped[str] = mapped_column(String(16))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class ExerciseSessionRow(Base):
    __tablename__ = "exercise_sessions"
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), primary_key=True
    )
    session_id: Mapped[str] = mapped_column(String(180), primary_key=True)
    daily_plan_date: Mapped[date] = mapped_column(Date, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class ExerciseAnswerRow(Base):
    __tablename__ = "exercise_answers"
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), primary_key=True
    )
    session_id: Mapped[str] = mapped_column(String(180), primary_key=True)
    exercise_id: Mapped[str] = mapped_column(String(180), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(String(36), unique=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class MasteryStateRow(Base):
    __tablename__ = "mastery_states"
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), primary_key=True
    )
    state_id: Mapped[str] = mapped_column(String(240), primary_key=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class MasteryEvidenceRow(Base):
    __tablename__ = "mastery_evidence"
    application_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), index=True
    )
    event_id: Mapped[str] = mapped_column(String(36), index=True)
    state_id: Mapped[str] = mapped_column(String(240))
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    engine_version: Mapped[str] = mapped_column(String(80))
    __table_args__ = (UniqueConstraint("learner_id", "event_id", "state_id"),)


class LearningEventRow(Base):
    __tablename__ = "learning_events"
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), primary_key=True
    )
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    server_received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)
    __table_args__ = (
        Index("ix_learning_events_learner_received", "learner_id", "server_received_at"),
    )


class CurriculumStateRow(Base):
    __tablename__ = "curriculum_states"
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), primary_key=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class PartnerRelationshipRow(Base):
    __tablename__ = "partner_relationships"
    relationship_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), index=True
    )
    partner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class PartnerPermissionRow(Base):
    __tablename__ = "partner_permissions"
    relationship_id: Mapped[str] = mapped_column(
        ForeignKey("partner_relationships.relationship_id", ondelete="CASCADE"), primary_key=True
    )
    daily_activity: Mapped[bool] = mapped_column(Boolean)
    progress_analytics: Mapped[bool] = mapped_column(Boolean)
    ai_analysis: Mapped[bool] = mapped_column(Boolean)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PartnerInvitationRow(Base):
    __tablename__ = "partner_invitations"
    code_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class ProgressAnalyticsRow(Base):
    __tablename__ = "progress_analytics"
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), primary_key=True
    )
    period_key: Mapped[str] = mapped_column(String(120), primary_key=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class AIReportRow(Base):
    __tablename__ = "ai_reports"
    report_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    relationship_id: Mapped[str] = mapped_column(
        ForeignKey("partner_relationships.relationship_id", ondelete="CASCADE"), index=True
    )
    created_by_partner_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class AIConversationRow(Base):
    __tablename__ = "ai_conversations"
    conversation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    relationship_id: Mapped[str] = mapped_column(
        ForeignKey("partner_relationships.relationship_id", ondelete="CASCADE"), index=True
    )
    created_by_partner_id: Mapped[str] = mapped_column(String(36), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class AIMessageRow(Base):
    __tablename__ = "ai_messages"
    message_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("ai_conversations.conversation_id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    role: Mapped[str] = mapped_column(String(24))
    content: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class HouseholdProfileRow(Base):
    """Two permanent aliases; legacy learner IDs and their progress remain intact."""
    __tablename__ = "household_profiles"
    role: Mapped[str] = mapped_column(String(16), primary_key=True)
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id"), unique=True
    )
    __table_args__ = (CheckConstraint("role IN ('husband', 'wife')", name="ck_household_role"),)


class LearningQualityRow(Base):
    __tablename__ = "learning_quality"
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="CASCADE"), primary_key=True
    )
    key: Mapped[str] = mapped_column(String(240), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class StudyProgramRow(Base):
    __tablename__ = "study_programs"
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id"), primary_key=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class StudyEventRow(Base):
    __tablename__ = "study_events"
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id"), primary_key=True
    )
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONDocument)


class FirebaseIdentityRow(Base):
    """Administrative allowlist: one Firebase identity per existing learner."""

    __tablename__ = "firebase_identities"
    firebase_uid: Mapped[str] = mapped_column(String(128), primary_key=True)
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("learner_profiles.learner_id", ondelete="RESTRICT"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
