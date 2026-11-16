import io
import json
import warnings
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request, Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.db.database import get_database
from app.modules.practice.models import AvatarRow, SpeakingAttemptRow
from app.modules.practice.service import PracticeService

router = APIRouter(prefix="/practice", tags=["practice"])
Identity = Annotated[AuthenticatedUser, Depends(get_current_user)]


def private(response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Authorization"


router.dependencies.append(Depends(private))


@router.get("/history")
def history(
    identity: Identity,
    module: Literal["all", "listening", "reading", "writing", "speaking"] = "all",
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    order: Literal["asc", "desc"] = "desc",
    day: date | None = None,
):
    return PracticeService().history(
        identity.uid, module, page, limit, order, day.isoformat() if day else None
    )


@router.get("/history/{attempt_id}")
def detail(attempt_id: UUID, identity: Identity, include_reviews: bool = True):
    return PracticeService().detail(identity.uid, str(attempt_id), include_reviews)


@router.get("/activity")
def activity(identity: Identity):
    return PracticeService().activity(identity.uid)


class SpeakingCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: UUID
    task_id: str = Field(min_length=1, max_length=100)


@router.post("/speaking/attempts", status_code=201)
def complete_speaking(body: SpeakingCompletion, identity: Identity):
    # Reuse the current Speaking catalogue; no parallel question generator.
    source = Path(__file__).resolve().parents[2] / "content/speaking_v1/catalog.json"
    if not source.exists():
        source = Path(__file__).resolve().parents[4] / "web/src/features/speaking/content.json"
    task = next(
        (q for q in json.loads(source.read_text())["questions"] if q["id"] == body.task_id), None
    )
    if task is None:
        raise NotFoundError("Speaking task not found.")
    with get_database().session() as s:
        s.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 7460))"),
            {"key": identity.uid},
        )
        old = s.scalar(
            select(SpeakingAttemptRow).where(
                SpeakingAttemptRow.owner == identity.uid,
                SpeakingAttemptRow.event_id == str(body.event_id),
            )
        )
        if old:
            if old.task_id != body.task_id:
                raise ConflictError("Event belongs to another task.")
            return {"id": old.id, "completed_at": old.completed_at.astimezone(UTC)}
        row = SpeakingAttemptRow(
            id=str(uuid4()),
            owner=identity.uid,
            event_id=str(body.event_id),
            task_id=body.task_id,
            task_snapshot=task,
            completed_at=datetime.now(UTC),
        )
        s.add(row)
        return {"id": row.id, "completed_at": row.completed_at}


@router.get("/avatar")
def avatar(identity: Identity):
    with get_database().session() as s:
        row = s.get(AvatarRow, identity.uid)
        if not row:
            raise NotFoundError("Avatar not found.")
        return Response(
            row.data,
            media_type="image/webp",
            headers={
                "Cache-Control": "private, no-store",
                "Vary": "Authorization",
                "X-Content-Type-Options": "nosniff",
                "ETag": row.revision,
            },
        )


@router.put("/avatar")
async def upload_avatar(request: Request, identity: Identity):
    data = bytearray()
    async for part in request.stream():
        data.extend(part)
        if len(data) > 2 * 1024 * 1024:
            raise ValidationError("Image must be no larger than 2 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if (
                    image.format not in {"PNG", "JPEG", "WEBP"}
                    or getattr(image, "n_frames", 1) != 1
                ):
                    raise ValueError()
                if (
                    not 32 <= min(image.size)
                    or max(image.size) > 4096
                    or image.width * image.height > 16000000
                ):
                    raise ValueError()
                image.load()
                normalized = ImageOps.fit(ImageOps.exif_transpose(image).convert("RGB"), (256, 256))
                output = io.BytesIO()
                normalized.save(output, "WEBP", quality=85)
                if len(output.getvalue()) > 128 * 1024:
                    raise ValueError()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise ValidationError("Use a static PNG, JPEG or WebP, 32–4096 pixels.") from None
    with get_database().session() as s:
        s.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 7461))"),
            {"key": identity.uid},
        )
        row = s.get(AvatarRow, identity.uid)
        if row is None:
            row = AvatarRow(owner=identity.uid)
            s.add(row)
        row.data = output.getvalue()
        row.revision = str(uuid4())
        row.updated_at = datetime.now(UTC)
        return {"saved": True, "revision": row.revision}


@router.delete("/avatar")
def remove_avatar(identity: Identity):
    with get_database().session() as s:
        s.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 7461))"),
            {"key": identity.uid},
        )
        row = s.get(AvatarRow, identity.uid)
        if row:
            s.delete(row)
    return {"deleted": True}


@router.get("/drafts")
def drafts(identity: Identity, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=50)):
    from app.modules.practice.learning import LearningService

    return LearningService().drafts(identity.uid, page, limit)


@router.get("/mistakes")
def mistakes(
    identity: Identity,
    module: Literal["all", "listening", "reading", "writing", "speaking"] = "all",
    search: str = Query("", max_length=200),
    order: Literal["newest", "oldest", "unreviewed"] = "newest",
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    include_reviews: bool = True,
):
    from app.modules.practice.learning import LearningService

    return LearningService().mistakes(
        identity.uid, module, search, order, page, limit, include_reviews
    )


class ReviewState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    module: Literal["listening", "reading", "writing", "speaking"]
    attempt_id: UUID
    item_key: str = Field(min_length=1, max_length=150)
    reviewed: bool


@router.put("/mistakes/state")
def review_state(body: ReviewState, identity: Identity):
    from app.modules.practice.learning import LearningService

    return LearningService().mark(
        identity.uid, body.module, str(body.attempt_id), body.item_key, body.reviewed
    )


@router.get("/analytics")
def analytics(identity: Identity, period: Literal["30", "90", "all"] = "30"):
    from app.modules.practice.learning import LearningService

    return LearningService().analytics(identity.uid, period)


@router.get("/reviews/{module}/{attempt_id}")
def stored_reviews(
    module: Literal["listening", "reading"],
    attempt_id: UUID,
    identity: Identity,
    question: str | None = Query(None, max_length=100),
):
    from app.modules.practice.reviews import read_saved_reviews

    return read_saved_reviews(module, identity.uid, str(attempt_id), question)
