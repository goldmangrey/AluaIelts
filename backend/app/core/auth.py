from typing import Annotated

from fastapi import Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.firebase_auth import verify_firebase_token
from app.db.database import get_database
from app.db.models import FirebaseIdentityRow
from app.modules.enrollment.repository import DeviceEnrollmentRepository

bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    uid: str
    enrollment_id: str | None = None
    provider: str = "legacy"
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

    settings = get_settings()
    if "." in token:
        if not settings.firebase_auth_enabled or token.count(".") != 2:
            raise UnauthorizedError("Unsupported credential.")
        firebase_uid = await run_in_threadpool(verify_firebase_token, token)

        def resolve() -> str | None:
            with get_database().session() as session:
                row = session.get(FirebaseIdentityRow, firebase_uid)
                return row.learner_id if row else None

        learner_id = await run_in_threadpool(resolve)
        if learner_id is None:
            raise ForbiddenError("This account has no Alua access.", "identity_not_allowed")
        return AuthenticatedUser(uid=learner_id, provider="firebase")
    if not settings.legacy_auth_enabled or not token.startswith("alua_dev_"):
        raise UnauthorizedError("Unsupported credential.")
    enrollment = await run_in_threadpool(DeviceEnrollmentRepository(get_database()).resolve, token)
    if enrollment is None:
        raise UnauthorizedError(
            message="The device token is invalid or revoked.", code="unauthorized"
        )
    return AuthenticatedUser(
        uid=enrollment.learner_id,
        enrollment_id=enrollment.enrollment_id,
    )
