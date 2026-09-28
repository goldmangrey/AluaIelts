from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class UserRole(StrEnum):
    LEARNER = "learner"
    PARTNER = "partner"


class EnglishLevel(StrEnum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class UserProfile(BaseModel):
    uid: str
    email: str | None = None
    display_name: str | None = None
    role: UserRole = UserRole.LEARNER
    current_level: EnglishLevel | None = None
    target_ielts_band: float | None = None
    daily_study_minutes: int | None = None
    created_at: datetime
    updated_at: datetime
