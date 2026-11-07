from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, Request, Response
from fastapi.responses import FileResponse

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.database import get_database
from app.modules.listening.catalog import audio_mime, get_catalog
from app.modules.listening.schemas import CreateAttempt, Submit, Sync
from app.modules.listening.service import ListeningService


def private(response: Response):
    response.headers["Cache-Control"] = "private, no-store"


router = APIRouter(prefix="/listening", tags=["listening"], dependencies=[Depends(private)])
Identity = Annotated[AuthenticatedUser, Depends(get_current_user)]


def get_service():
    return ListeningService(get_database(), get_catalog())


Service = Annotated[ListeningService, Depends(get_service)]


@router.get("/exams")
def catalog(identity: Identity, service: Service):
    return service.library(identity.uid)


@router.get("/exams/{exam_id}")
def exam(exam_id: str, identity: Identity, service: Service):
    return {
        "exam": service.catalog.public_exam(service.catalog.exam(exam_id)),
        "metadata": next(
            e for e in service.library(identity.uid)["items"] if e["exam_id"] == exam_id
        ),
    }


@router.post("/attempts", status_code=201)
def start(body: CreateAttempt, identity: Identity, service: Service):
    return service.create(identity.uid, body)


@router.get("/attempts/{attempt_id}")
def attempt(attempt_id: UUID, identity: Identity, service: Service):
    return service.get(identity.uid, str(attempt_id))


@router.post("/attempts/{attempt_id}/sync")
def sync(attempt_id: UUID, body: Sync, identity: Identity, service: Service):
    return service.mutate(identity.uid, str(attempt_id), "sync", body)


@router.post("/attempts/{attempt_id}/submit")
def submit(attempt_id: UUID, body: Submit, identity: Identity, service: Service):
    return service.mutate(identity.uid, str(attempt_id), "submit", body)


@router.get("/attempts/{attempt_id}/result")
def result(attempt_id: UUID, identity: Identity, service: Service):
    return service.result(identity.uid, str(attempt_id))


@router.get("/attempts/{attempt_id}/review")
def review(attempt_id: UUID, identity: Identity, service: Service):
    return service.result(identity.uid, str(attempt_id), True)


@router.post("/attempts/{attempt_id}/playback")
def playback(attempt_id: UUID, identity: Identity, service: Service):
    return service.grant(identity.uid, str(attempt_id))


@router.get("/attempts/{attempt_id}/assets/{asset_id}")
def asset(attempt_id: UUID, asset_id: str, identity: Identity, service: Service):
    return FileResponse(
        service.asset(identity.uid, str(attempt_id), asset_id),
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.api_route("/attempts/{attempt_id}/audio/{part}", methods=["GET", "HEAD"])
def audio(
    request: Request,
    attempt_id: UUID,
    part: Annotated[int, Path(ge=1, le=4)],
    service: Service,
    x_playback_grant: Annotated[str | None, Header()] = None,
):
    record = service.playback_record(str(attempt_id), part, x_playback_grant)
    path = service.catalog.audio_path(record)
    return FileResponse(
        path,
        media_type=audio_mime(path),
        headers={
            "Cache-Control": "private, no-store",
            "Vary": "X-Playback-Grant",
            "X-Content-Type-Options": "nosniff",
        },
        content_disposition_type="inline",
    )


@router.get("/attempts/{attempt_id}/ai-review/{number}/context")
def ai_context(
    attempt_id: UUID,
    number: Annotated[int, Path(ge=1, le=40)],
    identity: Identity,
    service: Service,
):
    from app.modules.listening.ai_review import AIReview

    return AIReview(service).context(identity.uid, str(attempt_id), number)


@router.post("/attempts/{attempt_id}/ai-review/{number}")
def ai_review(
    attempt_id: UUID,
    number: Annotated[int, Path(ge=1, le=40)],
    identity: Identity,
    service: Service,
    authorization: Annotated[str, Header()],
):
    from app.modules.listening.ai_review import AIReview

    return AIReview(service).explain(identity.uid, str(attempt_id), number, authorization)
