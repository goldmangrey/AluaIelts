from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class PartnerInviteStatus(StrEnum):
    ACTIVE = "active"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class PartnerRelationshipStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class PartnerSharingSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    share_daily_activity: bool = True
    share_progress_analytics: bool = True
    share_learning_profile: bool = True
    share_recent_error_patterns: bool = True
    allow_ai_progress_analysis: bool = False


class PartnerInvitation(BaseModel):
    model_config = ConfigDict(frozen=True)

    invite_id: str
    learner_uid: str
    code_hash: str
    status: PartnerInviteStatus = PartnerInviteStatus.ACTIVE
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None = None
    accepted_by_uid: str | None = None


class PartnerRelationship(BaseModel):
    model_config = ConfigDict(frozen=True)

    relationship_id: str
    learner_uid: str
    partner_uid: str
    status: PartnerRelationshipStatus = PartnerRelationshipStatus.ACTIVE
    sharing_settings: PartnerSharingSettings
    created_at: datetime
    updated_at: datetime
    revoked_at: datetime | None = None
