"""Self-service provisioning; passwords and client identity claims are never accepted."""

from collections import deque
from threading import Lock
from time import monotonic
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.auth import bearer_scheme
from app.core.config import get_settings
from app.core.exceptions import AluaError, ExternalServiceError, UnauthorizedError
from app.core.firebase_auth import verify_firebase_token
from app.db.database import Database, get_database
from app.db.models import FirebaseIdentityRow, LearnerProfileRow
from app.db.serialization import document
from app.modules.users.models import UserProfile
from app.modules.users.schemas import UserProfileResponse

router = APIRouter(prefix="/auth", tags=["authentication"])
# Bounded, process-local pre-verification budget; no forwarded-header/IP trust.
# Database creation cap below is durable and shared across all API workers.
_verification_times: deque[float] = deque()
_budget_lock = Lock()


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value or any(ord(c) < 32 for c in value):
                raise ValueError("Enter a valid name")
        return value


def consume_verification_budget() -> None:
    now = monotonic()
    with _budget_lock:
        while _verification_times and _verification_times[0] <= now - 60:
            _verification_times.popleft()
        if len(_verification_times) >= get_settings().registration_requests_per_minute:
            raise AluaError("Please retry later.", "registration_throttled", 429)
        _verification_times.append(now)


def provision(database: Database, firebase_uid: str, name: str | None) -> UserProfile:
    try:
        with database.session() as session:
            # Shared with private identity administration; serializes same-UID retries
            # AND enforces the creation budget across workers in the same transaction.
            session.execute(text("SELECT pg_advisory_xact_lock(19770429, 2)"))
            identity = session.get(FirebaseIdentityRow, firebase_uid)
            if identity:
                row = session.get(LearnerProfileRow, identity.learner_id)
                if row is None:
                    raise ExternalServiceError("Profile unavailable.", "registration_unavailable")
                return UserProfile.model_validate(row.payload)
            recent = session.scalar(
                select(func.count())
                .select_from(FirebaseIdentityRow)
                .where(FirebaseIdentityRow.created_at > func.now() - text("INTERVAL '1 hour'"))
            )
            if recent >= get_settings().registration_creations_per_hour:
                raise AluaError("Please retry later.", "registration_throttled", 429)
            now = session.scalar(select(func.now()))
            profile = UserProfile(
                uid=str(uuid4()), display_name=name or "Learner", created_at=now, updated_at=now
            )
            session.add(
                LearnerProfileRow(
                    learner_id=profile.uid,
                    display_name=profile.display_name,
                    created_at=now,
                    updated_at=now,
                    payload=document(profile),
                )
            )
            session.flush()
            session.add(
                FirebaseIdentityRow(
                    firebase_uid=firebase_uid, learner_id=profile.uid, created_at=now
                )
            )
            session.flush()
        return profile
    except SQLAlchemyError as error:
        # Transaction is rolled back, including the learner insert. Retrying is safe.
        raise ExternalServiceError(
            "Please retry completing registration.", "registration_unavailable"
        ) from error


@router.post("/register", response_model=UserProfileResponse)
async def register(
    body: RegisterRequest,
    response: Response,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    database: Annotated[Database, Depends(get_database)],
) -> UserProfileResponse:
    response.headers["Cache-Control"] = "no-store"
    settings = get_settings()
    if not settings.firebase_auth_enabled:
        raise UnauthorizedError("Firebase authentication is unavailable.")
    if not settings.self_registration_enabled:
        raise ExternalServiceError(
            "Registration is temporarily unavailable.", "registration_disabled"
        )
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or credentials.credentials.count(".") != 2
        or len(credentials.credentials) > 16384
    ):
        raise UnauthorizedError("A Firebase ID token is required.")
    consume_verification_budget()
    uid = await run_in_threadpool(verify_firebase_token, credentials.credentials)
    profile = await run_in_threadpool(provision, database, uid, body.display_name)
    return UserProfileResponse.from_profile(profile)
