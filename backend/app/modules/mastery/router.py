from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.database import get_database
from app.modules.grammar.content_repository import get_grammar_content_repository
from app.modules.mastery.engine import MasteryEngine
from app.modules.mastery.models import (
    MasteryContentType,
    MasteryDimension,
    MasteryLevel,
    MasteryState,
)
from app.modules.mastery.repository import MasteryRepository
from app.modules.mastery.schemas import ContentMasterySummary, MasteryStatesResponse
from app.modules.mastery.service import MasteryService
from app.modules.vocabulary.content_repository import get_vocabulary_content_repository

router = APIRouter(prefix="/mastery", tags=["mastery"])


def get_mastery_service() -> MasteryService:
    return MasteryService(
        repository=MasteryRepository(get_database()),
        engine=MasteryEngine(),
        vocabulary=get_vocabulary_content_repository(),
        grammar=get_grammar_content_repository(),
    )


@router.get("", response_model=MasteryStatesResponse)
async def list_mastery_states(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[MasteryService, Depends(get_mastery_service)],
    content_type: MasteryContentType | None = None,
    dimension: MasteryDimension | None = None,
    level: MasteryLevel | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> MasteryStatesResponse:
    items = await run_in_threadpool(
        service.list_states,
        identity.uid,
        content_type=content_type,
        dimension=dimension,
        level=level,
        limit=limit,
        offset=offset,
    )
    return MasteryStatesResponse(items=items, limit=limit, offset=offset)


@router.get("/content/{content_type}/{content_id}", response_model=ContentMasterySummary)
async def get_content_mastery(
    content_type: MasteryContentType,
    content_id: str,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[MasteryService, Depends(get_mastery_service)],
) -> ContentMasterySummary:
    return await run_in_threadpool(
        service.get_content_summary, identity.uid, content_type, content_id
    )


@router.get("/{state_id}", response_model=MasteryState)
async def get_mastery_state(
    state_id: str,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[MasteryService, Depends(get_mastery_service)],
) -> MasteryState:
    return await run_in_threadpool(service.get_state, identity.uid, state_id)
