from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.users.models import UserProfile


class EnrollDeviceRequest(BaseModel):
    code: str = Field(pattern=r"^[0-9a-fA-F]{32}$")
    device_name: str | None = Field(default=None, min_length=1, max_length=160)


class EnrollDeviceResponse(BaseModel):
    token: str
    enrollment_id: str
    profile: UserProfile


class DeviceEnrollmentResponse(BaseModel):
    enrollment_id: str
    device_name: str | None
    created_at: datetime
    last_used_at: datetime | None
    is_current: bool = False


class DeviceEnrollmentListResponse(BaseModel):
    devices: list[DeviceEnrollmentResponse]


class DeviceRevocationResponse(BaseModel):
    revoked: bool
