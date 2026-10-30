from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.auth import AuthenticatedUser, get_current_user
from app.modules.vocabulary.content_repository import get_vocabulary_content_repository
from app.modules.vocabulary.models import PartOfSpeech, VocabularyItem, VocabularyTopic
from app.modules.vocabulary.schemas import (
    CurriculumVocabularyResponse,
    VocabularyListResponse,
    VocabularyTrackDetail,
    VocabularyTrackSummary,
)
from app.modules.vocabulary.service import VocabularyService

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])


def get_vocabulary_service() -> VocabularyService:
    return VocabularyService(get_vocabulary_content_repository())


@router.get("", response_model=VocabularyListResponse)
async def list_vocabulary(
    _: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[VocabularyService, Depends(get_vocabulary_service)],
    q: str | None = Query(default=None, min_length=1, max_length=100),
    cefr: str | None = None,
    topic: VocabularyTopic | None = None,
    part_of_speech: PartOfSpeech | None = None,
    track_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> VocabularyListResponse:
    return service.list_items(
        query=q,
        cefr=cefr,
        topic=topic,
        part_of_speech=part_of_speech,
        track_id=track_id,
        limit=limit,
        offset=offset,
    )


@router.get("/items/{item_id}", response_model=VocabularyItem)
async def get_vocabulary_item(
    item_id: str,
    _: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[VocabularyService, Depends(get_vocabulary_service)],
) -> VocabularyItem:
    return service.get_item(item_id)


@router.get("/tracks", response_model=list[VocabularyTrackSummary])
async def list_vocabulary_tracks(
    _: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[VocabularyService, Depends(get_vocabulary_service)],
) -> list[VocabularyTrackSummary]:
    return service.list_tracks()


@router.get("/tracks/{track_id}", response_model=VocabularyTrackDetail)
async def get_vocabulary_track(
    track_id: str,
    _: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[VocabularyService, Depends(get_vocabulary_service)],
) -> VocabularyTrackDetail:
    return service.get_track(track_id)


@router.get(
    "/curriculum-nodes/{node_id}",
    response_model=CurriculumVocabularyResponse,
)
async def get_curriculum_vocabulary(
    node_id: str,
    _: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[VocabularyService, Depends(get_vocabulary_service)],
) -> CurriculumVocabularyResponse:
    return service.get_curriculum_node(node_id)
