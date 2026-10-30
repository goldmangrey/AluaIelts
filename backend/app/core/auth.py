from typing import Annotated

from fastapi import Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.exceptions import UnauthorizedError
from app.db.database import get_database
from app.modules.enrollment.repository import DeviceEnrollmentRepository

bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    uid: str
    enrollment_id: str
    email: str | None = None
    name: str | None = None


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError(
            message="A valid bearer token is required.",
            code="unauthorized",
        )
    token = credentials.credentials.strip()
    if not token:
        raise UnauthorizedError(message="A bearer token is required.", code="unauthorized")

    enrollment = await run_in_threadpool(DeviceEnrollmentRepository(get_database()).resolve, token)
    if enrollment is None:
        raise UnauthorizedError(
            message="The device token is invalid or revoked.", code="unauthorized"
        )
    return AuthenticatedUser(
        uid=enrollment.learner_id,
        enrollment_id=enrollment.enrollment_id,
    )
