from datetime import date, datetime

from pydantic import BaseModel, Field

from app.modules.partner.models import PartnerSharingSettings
from app.modules.progress.models import ProgressErrorPattern, ProgressSnapshot
from app.modules.student_model.models import (
    StudentModelCurriculum,
    StudentModelDataQuality,
    StudentModelMasteryOverview,
    StudentModelStrength,
    StudentModelWeakness,
)


class AcceptPartnerInviteRequest(BaseModel):
    code: str = Field(min_length=8, max_length=32)


class PartnerInviteResponse(BaseModel):
    invite_id: str
    code: str
    expires_at: datetime


class PartnerRelationshipSummary(BaseModel):
    relationship_id: str
    display_name: str
    connected_at: datetime
    sharing_settings: PartnerSharingSettings


class PartnerStatusResponse(BaseModel):
    sharing_my_progress: PartnerRelationshipSummary | None = None
    monitoring_learner: PartnerRelationshipSummary | None = None


class PartnerLearnerSummary(BaseModel):
    display_name: str


class PartnerTodayActivity(BaseModel):
    local_date: date
    has_plan: bool
    target_minutes: int | None = None
    estimated_minutes: int | None = None
    estimated_completed_minutes: int = 0
    total_items: int = 0
    completed_items: int = 0
    remaining_items: int = 0
    plan_status: str | None = None
    current_focus: str | None = None
    grammar_items: int = 0
    vocabulary_items: int = 0
    review_items: int = 0


class PartnerLearningProfile(BaseModel):
    curriculum: StudentModelCurriculum
    mastery: StudentModelMasteryOverview
    strengths: list[StudentModelStrength]
    weaknesses: list[StudentModelWeakness]
    data_quality: StudentModelDataQuality


class PartnerDashboardSnapshot(BaseModel):
    learner: PartnerLearnerSummary
    relationship_id: str
    connected_at: datetime
    permissions: PartnerSharingSettings
    today_activity: PartnerTodayActivity | None = None
    progress: ProgressSnapshot | None = None
    learning_profile: PartnerLearningProfile | None = None
    recent_errors: list[ProgressErrorPattern] | None = None
    generated_at: datetime
