import math
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.exceptions import (
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from app.db.database import get_database
from app.modules.writing.bridge import verify_bridge
from app.modules.writing.contract import validate_assessment, words
from app.modules.writing.models import WritingAttemptRow as Attempt
from app.modules.writing.models import WritingTaskRow as Task


def private(response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Authorization"


class PrivateWritingRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request):
            try:
                return await original(request)
            except SQLAlchemyError:
                # SQLAlchemy exceptions can contain SQL parameters, including private essays.
                raise ExternalServiceError("Writing storage is temporarily unavailable.") from None

        return handler


router = APIRouter(
    route_class=PrivateWritingRoute,
    prefix="/writing",
    tags=["writing"],
    dependencies=[Depends(get_current_user), Depends(private)],
)
Identity = Annotated[AuthenticatedUser, Depends(get_current_user)]


class Create(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(pattern=r"^writing-t2-\d{6}$")
    event_id: UUID
    reuse_draft: bool = True


class Save(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0)
    essay: str = Field(max_length=16000)


class Version(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0)


class Completion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lease: UUID
    failure_kind: (
        Literal[
            "rate_limited",
            "provider_unavailable",
            "invalid_response",
            "configuration_error",
            "transport_error",
        ]
        | None
    ) = None
    review: dict | None = None
    provider: str = Field(default="", max_length=32)
    model: str = Field(default="", max_length=128)


def lock_owner(s, uid):
    s.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:uid, 8721))"), {"uid": uid})


def own(s, uid, aid):
    row = s.scalar(
        select(Attempt).where(Attempt.id == str(aid), Attempt.owner == uid).with_for_update()
    )
    if row is None:
        raise NotFoundError("Writing attempt not found.")
    return row


def serial(a):
    return {
        k: getattr(a, k)
        for k in (
            "id",
            "task_id",
            "version",
            "essay",
            "word_count",
            "status",
            "created_at",
            "updated_at",
            "assessment",
            "ai_status",
        )
    } | {"task": a.task_snapshot}


@router.get("/tasks")
def tasks(identity: Identity):
    with get_database().session() as s:
        return {
            "items": [
                r.payload
                for r in s.scalars(
                    select(Task)
                    .where(Task.payload["publication_status"].as_string() == "READY")
                    .order_by(Task.id)
                )
            ]
        }


@router.get("/tasks/{task_id}")
def task(task_id: str, identity: Identity):
    with get_database().session() as s:
        row = s.get(Task, task_id)
        if row is None or row.payload.get("publication_status") != "READY":
            raise NotFoundError("Writing task not found.")
        return row.payload


@router.post("/attempts", status_code=201)
def create(data: Create, identity: Identity):
    with get_database().session() as s:
        lock_owner(s, identity.uid)
        t = s.get(Task, data.task_id)
        if t is None or t.payload.get("publication_status") != "READY":
            raise NotFoundError("Writing task not found.")
        old = s.scalar(
            select(Attempt).where(
                Attempt.owner == identity.uid, Attempt.event_id == str(data.event_id)
            )
        )
        if old:
            if old.task_id != data.task_id:
                raise ConflictError("Idempotency key reused for another task.")
            return serial(old)
        if data.reuse_draft:
            old = s.scalar(
                select(Attempt)
                .where(
                    Attempt.owner == identity.uid,
                    Attempt.task_id == data.task_id,
                    Attempt.status == "draft",
                )
                .order_by(Attempt.updated_at.desc())
            )
            if old:
                return serial(old)
        now = datetime.now(UTC)
        a = Attempt(
            id=str(uuid4()),
            owner=identity.uid,
            task_id=t.id,
            task_snapshot=t.payload,
            event_id=str(data.event_id),
            version=0,
            essay="",
            word_count=0,
            status="draft",
            ai_status="idle",
            ai_calls=0,
            created_at=now,
            updated_at=now,
        )
        s.add(a)
        s.flush()
        return serial(a)


@router.get("/attempts")
def attempts(identity: Identity, limit: int = Query(100, ge=1, le=100)):
    with get_database().session() as s:
        return {
            "items": [
                serial(a)
                for a in s.scalars(
                    select(Attempt)
                    .where(Attempt.owner == identity.uid)
                    .order_by(Attempt.updated_at.desc())
                    .limit(limit)
                )
            ]
        }


@router.get("/attempts/{aid}")
def attempt(aid: UUID, identity: Identity):
    with get_database().session() as s:
        return serial(own(s, identity.uid, aid))


@router.put("/attempts/{aid}")
def save(aid: UUID, data: Save, identity: Identity):
    try:
        data.essay.encode("utf-8")
        if any(ord(c) < 32 and c not in "\n\r\t" for c in data.essay):
            raise ValueError()
    except (UnicodeError, ValueError):
        raise ValidationError("Unsupported text characters.", "invalid_essay") from None
    if words(data.essay) > 2000:
        raise ValidationError("Maximum 2,000 words.", "essay_too_long")
    with get_database().session() as s:
        a = own(s, identity.uid, aid)
        if a.status != "draft":
            raise ConflictError("Submitted essays are immutable.")
        # A retried save can be acknowledged without another version increment.
        if a.essay == data.essay:
            return serial(a)
        if a.version != data.expected_version:
            raise ConflictError("A newer draft exists. Your text is retained.", "draft_conflict")
        a.essay, a.word_count = data.essay, words(data.essay)
        a.version += 1
        a.updated_at = datetime.now(UTC)
        return serial(a)


@router.post("/attempts/{aid}/submit")
def submit(aid: UUID, data: Version, identity: Identity):
    with get_database().session() as s:
        a = own(s, identity.uid, aid)
        if a.version != data.expected_version:
            raise ConflictError("Save the current version first.")
        # MVP does not provide unreliable numerical estimates for underlength scripts.
        if a.word_count < 250:
            raise ValidationError("Write at least 250 words before AI review.", "essay_too_short")
        a.status = "submitted"
        return serial(a)


@router.post("/attempts/{aid}/assessment/claim", dependencies=[Depends(verify_bridge)])
def claim(aid: UUID, identity: Identity):
    with get_database().session() as s:
        lock_owner(s, identity.uid)
        a = own(s, identity.uid, aid)
        if a.assessment:
            return {"cached": True, "attempt": serial(a)}
        if a.status != "submitted":
            raise ConflictError("Submit an immutable essay first.")
        now = datetime.now(UTC)
        if a.ai_status == "pending" and a.ai_started_at > now - timedelta(seconds=180):
            raise ConflictError("Assessment is already running.", "assessment_pending")
        recent = list(
            s.scalars(
                select(Attempt).where(
                    Attempt.owner == identity.uid, Attempt.ai_started_at > now - timedelta(hours=1)
                )
            )
        )
        if a.ai_calls >= 3:
            return JSONResponse(
                status_code=429,
                headers={"Cache-Control": "private, no-store", "Vary": "Authorization"},
                content={
                    "error": {
                        "code": "writing_attempt_limit",
                        "source": "application",
                        "kind": "rate_limited",
                        "retryable": False,
                    }
                },
            )
        total = sum(x.ai_calls for x in recent)
        if total >= 6:
            # Preserve existing limits. Report only the actual expiry of this owner window.
            remaining = total
            retry_at = now
            for old in sorted(recent, key=lambda row: row.ai_started_at):
                remaining -= old.ai_calls
                retry_at = old.ai_started_at + timedelta(hours=1)
                if remaining < 6:
                    break
            seconds = max(1, math.ceil((retry_at - now).total_seconds()))
            return JSONResponse(
                status_code=429,
                headers={
                    "Cache-Control": "private, no-store",
                    "Retry-After": str(seconds),
                    "Vary": "Authorization",
                },
                content={
                    "error": {
                        "code": "writing_rate_limited",
                        "source": "application",
                        "kind": "rate_limited",
                        "retryable": True,
                    }
                },
            )
        a.ai_status, a.ai_lease, a.ai_started_at = "pending", str(uuid4()), now
        a.ai_calls += 1
        return {
            "cached": False,
            "failure_protocol": 1,
            "lease": a.ai_lease,
            "essay": a.essay,
            "task": a.task_snapshot,
            "word_count": a.word_count,
            "version": a.version,
        }


@router.post("/attempts/{aid}/assessment/complete", dependencies=[Depends(verify_bridge)])
def complete(aid: UUID, data: Completion, identity: Identity):
    with get_database().session() as s:
        a = own(s, identity.uid, aid)
        if a.assessment:
            return serial(a)
        if a.ai_lease != str(data.lease) or a.ai_status != "pending":
            raise ConflictError("Assessment lease expired.")
        if data.review is None:
            a.ai_status = data.failure_kind or "AI_UNAVAILABLE"
        else:
            try:
                review = validate_assessment(data.review, a.essay)
            except (ValueError, UnicodeError):
                # Never include model output or essays in operational errors/logs.
                raise ValidationError(
                    "AI evidence validation failed.", "invalid_assessment"
                ) from None
            if (
                data.provider not in ("groq", "cloudflare", "gemini", "openrouter")
                or not data.model
            ):
                raise ValidationError("Provider metadata missing.")
            a.assessment = review | {
                "provider": data.provider,
                "model": data.model,
                "assessed_at": datetime.now(UTC).isoformat(),
                "essay_version": a.version,
            }
            a.ai_status = "completed"
        return serial(a)
