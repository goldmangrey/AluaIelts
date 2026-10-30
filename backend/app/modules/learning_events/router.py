from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.database import get_database
from app.modules.curriculum.content_repository import get_curriculum_content_repository
from app.modules.grammar.content_repository import get_grammar_content_repository
from app.modules.learning_events.models import LearningEvent
from app.modules.learning_events.repository import LearningEventRepository
from app.modules.learning_events.schemas import CreateLearningEventRequest, LearningEventsResponse
from app.modules.learning_events.service import LearningEventService
from app.modules.vocabulary.content_repository import get_vocabulary_content_repository

router = APIRouter(prefix="/learning-events", tags=["learning-events"])


def get_learning_event_service() -> LearningEventService:
    return LearningEventService(
        repository=LearningEventRepository(get_database()),
        curriculum=get_curriculum_content_repository(),
        grammar=get_grammar_content_repository(),
        vocabulary=get_vocabulary_content_repository(),
    )


@router.post("", response_model=LearningEvent)
async def create_learning_event(
    request: CreateLearningEventRequest,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[LearningEventService, Depends(get_learning_event_service)],
) -> LearningEvent:
    return await run_in_threadpool(service.record_client_event, identity.uid, request)


@router.get("", response_model=LearningEventsResponse)
async def list_learning_events(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[LearningEventService, Depends(get_learning_event_service)],
    limit: int = Query(default=50, ge=1, le=100),
    before_server_received_at: datetime | None = None,
) -> LearningEventsResponse:
    events = await run_in_threadpool(
        service.list_recent,
        identity.uid,
        limit=limit,
        before_server_received_at=before_server_received_at,
    )
    return LearningEventsResponse(items=events, limit=limit)


@router.get("/{event_id}", response_model=LearningEvent)
async def get_learning_event(
    event_id: UUID,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[LearningEventService, Depends(get_learning_event_service)],
) -> LearningEvent:
    return await run_in_threadpool(service.get_event, identity.uid, event_id)
