from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import FileResponse

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.exceptions import NotFoundError
from app.db.database import get_database
from app.modules.reading.catalog import get_catalog
from app.modules.reading.repository import ReadingRepository
from app.modules.reading.schemas import (
    AnswerMutation,
    BatchMutation,
    CheckMutation,
    CreateAttempt,
    StateMutation,
    SubmitMutation,
)
from app.modules.reading.service import ReadingService


def no_store(response: Response):
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/reading", tags=["reading"], dependencies=[Depends(get_current_user), Depends(no_store)]
)
Identity = Annotated[AuthenticatedUser, Depends(get_current_user)]


def get_reading_service() -> ReadingService:
    return ReadingService(ReadingRepository(get_database()), get_catalog())


Service = Annotated[ReadingService, Depends(get_reading_service)]


@router.get("/books")
def books(identity: Identity, service: Service):
    library = service.library(identity.uid)
    return {
        "items": [
            {
                "book_number": book,
                "exams": [e for e in library["items"] if e["source_book"] == book],
            }
            for book in service.catalog.manifest["books"]
        ],
        "dataset_version": library["dataset_version"],
    }


@router.get("/exams")
def exams(identity: Identity, service: Service, book: int | None = Query(None, ge=4, le=21)):
    return service.library(identity.uid, book)


@router.get("/exams/{exam_id}")
def exam(exam_id: str, identity: Identity, service: Service):
    entry = service.catalog.enabled(exam_id)
    metadata = {k: v for k, v in entry.items() if k != "answer_key_hash"}
    return service.catalog.public_exam(service.catalog.exams[exam_id]) | {"metadata": metadata}


@router.post("/attempts", status_code=201)
def create_attempt(request: CreateAttempt, identity: Identity, service: Service):
    return service.create(identity.uid, request)


@router.get("/attempts")
def attempts(
    identity: Identity,
    service: Service,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return service.list(identity.uid, limit, offset)


@router.get("/attempts/{attempt_id}")
def attempt(attempt_id: UUID, identity: Identity, service: Service):
    return service.get(identity.uid, str(attempt_id))


@router.put("/attempts/{attempt_id}/answers/{question_id}")
def answer(
    attempt_id: UUID,
    question_id: str,
    request: AnswerMutation,
    identity: Identity,
    service: Service,
):
    return service.mutate(identity.uid, str(attempt_id), "answer", request, question_id=question_id)


@router.post("/attempts/{attempt_id}/sync")
def sync(attempt_id: UUID, request: BatchMutation, identity: Identity, service: Service):
    return service.mutate(identity.uid, str(attempt_id), "batch", request)


@router.patch("/attempts/{attempt_id}/state")
def state(attempt_id: UUID, request: StateMutation, identity: Identity, service: Service):
    return service.mutate(identity.uid, str(attempt_id), "state", request)


@router.post("/attempts/{attempt_id}/check")
def check(attempt_id: UUID, request: CheckMutation, identity: Identity, service: Service):
    return service.mutate(identity.uid, str(attempt_id), "check", request)


@router.post("/attempts/{attempt_id}/submit")
def submit(attempt_id: UUID, request: SubmitMutation, identity: Identity, service: Service):
    return service.mutate(identity.uid, str(attempt_id), "submit", request)


@router.get("/attempts/{attempt_id}/result")
def result(attempt_id: UUID, identity: Identity, service: Service):
    return service.result(identity.uid, str(attempt_id))


@router.get("/assets/{asset_id}")
def asset(asset_id: str, request: Request, identity: Identity):
    catalog = get_catalog()
    value = catalog.assets.get(asset_id)
    if value is None:
        raise NotFoundError("Reading asset not found.")
    etag = '"' + value["sha256"] + '"'
    headers = {
        "ETag": etag,
        "Cache-Control": "private, max-age=31536000, immutable",
        "X-Content-Type-Options": "nosniff",
        "Vary": "Authorization",
        "X-Image-Width": str(value["width"]),
        "X-Image-Height": str(value["height"]),
    }
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return FileResponse(catalog.path(value["path"]), media_type="image/png", headers=headers)
