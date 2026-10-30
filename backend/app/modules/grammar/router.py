from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.auth import AuthenticatedUser, get_current_user
from app.modules.grammar.content_repository import get_grammar_content_repository
from app.modules.grammar.models import GrammarLesson
from app.modules.grammar.schemas import GrammarListResponse, GrammarStageResponse
from app.modules.grammar.service import GrammarService

router = APIRouter(prefix="/grammar", tags=["grammar"])


def get_grammar_service() -> GrammarService:
    return GrammarService(get_grammar_content_repository())


@router.get("", response_model=GrammarListResponse)
async def list_grammar_lessons(
    _: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[GrammarService, Depends(get_grammar_service)],
    q: str | None = Query(default=None, min_length=1, max_length=100),
    cefr: str | None = None,
    stage_id: str | None = None,
    tag: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> GrammarListResponse:
    return service.list_lessons(
        query=q,
        cefr=cefr,
        stage_id=stage_id,
        tag=tag,
        limit=limit,
        offset=offset,
    )


@router.get("/lessons/{lesson_id}", response_model=GrammarLesson)
async def get_grammar_lesson(
    lesson_id: str,
    _: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[GrammarService, Depends(get_grammar_service)],
) -> GrammarLesson:
    return service.get_lesson(lesson_id)


@router.get("/stages/{stage_id}", response_model=GrammarStageResponse)
async def get_grammar_stage(
    stage_id: str,
    _: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[GrammarService, Depends(get_grammar_service)],
) -> GrammarStageResponse:
    return service.get_stage(stage_id)


@router.get("/curriculum-nodes/{node_id}", response_model=GrammarLesson)
async def get_curriculum_grammar_lesson(
    node_id: str,
    _: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[GrammarService, Depends(get_grammar_service)],
) -> GrammarLesson:
    return service.get_lesson_for_curriculum_node(node_id)
