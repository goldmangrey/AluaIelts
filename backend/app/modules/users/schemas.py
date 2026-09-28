from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.users.models import EnglishLevel, UserProfile, UserRole


class UserProfileResponse(BaseModel):
    uid: str
    email: str | None
    display_name: str | None
    role: UserRole
    current_level: EnglishLevel | None
    target_ielts_band: float | None
    daily_study_minutes: int | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_profile(cls, profile: UserProfile) -> "UserProfileResponse":
        return cls.model_validate(profile.model_dump())


class UserProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    current_level: EnglishLevel | None = None
    target_ielts_band: float | None = Field(default=None, ge=4.0, le=9.0)
    daily_study_minutes: int | None = Field(default=None, ge=5, le=240)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Display name must not be null.")
        value = value.strip()
        if not value:
            raise ValueError("Display name must not be empty.")
        return value
