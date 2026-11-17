"""Self-service provisioning; passwords and client identity claims are never accepted."""

from collections import OrderedDict, deque
from hashlib import sha256
from math import ceil
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
from app.core.firebase_auth import verify_firebase_identity
from app.db.database import Database, get_database
from app.db.models import FirebaseIdentityRow, LearnerProfileRow
from app.db.serialization import document
from app.modules.users.models import UserProfile
from app.modules.users.schemas import UserProfileResponse

router = APIRouter(prefix="/auth", tags=["authentication"])
# Bounded process-local token/verified-UID budgets; never trust client IP headers.
# Token budget protects verification; UID budget also covers ID-token rotation.
_verification_times: OrderedDict[str, deque[float]] = OrderedDict()
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


def throttled(seconds: float) -> AluaError:
    return AluaError(
        "Please retry later.",
        "registration_throttled",
        429,
        headers={"Retry-After": str(max(1, ceil(seconds))), "Cache-Control": "no-store"},
    )


def consume_verification_budget(key: str) -> None:
    now = monotonic()
    with _budget_lock:
        times = _verification_times.pop(key, deque())
        while times and times[0] <= now - 60:
            times.popleft()
        _verification_times[key] = times
        if len(_verification_times) > 10000:
            _verification_times.popitem(last=False)
        if len(times) >= get_settings().registration_requests_per_minute:
            raise throttled(times[0] + 60 - now)
        times.append(now)


def provision(
    database: Database, firebase_uid: str, name: str | None, verified_google: bool = False
) -> UserProfile:
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
            # Signed Google identities use a high emergency flood ceiling, not the
            # low unverified-account cap. Both are durable and shared across workers.
            settings = get_settings()
            creation_limit = (
                settings.registration_google_creations_per_hour
                if verified_google
                else settings.registration_creations_per_hour
            )
            if recent >= creation_limit:
                reset_at = session.scalar(
                    select(FirebaseIdentityRow.created_at)
                    .where(FirebaseIdentityRow.created_at > func.now() - text("INTERVAL '1 hour'"))
                    .order_by(FirebaseIdentityRow.created_at.desc())
                    .offset(creation_limit - 1)
                    .limit(1)
                )
                now = session.scalar(select(func.now()))
                raise throttled(3600 - (now - reset_at).total_seconds())
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
    consume_verification_budget("token:" + sha256(credentials.credentials.encode()).hexdigest())
    identity = await run_in_threadpool(verify_firebase_identity, credentials.credentials)
    consume_verification_budget("uid:" + identity.uid)
    profile = await run_in_threadpool(
        provision, database, identity.uid, body.display_name, identity.verified_google
    )
    return UserProfileResponse.from_profile(profile)
