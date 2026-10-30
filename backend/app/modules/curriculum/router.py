from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.database import get_database
from app.modules.curriculum.content_repository import get_curriculum_content_repository
from app.modules.curriculum.models import (
    CurriculumNode,
    CurriculumProgram,
    CurriculumStage,
    UserCurriculumOverview,
)
from app.modules.curriculum.service import CurriculumService
from app.modules.curriculum.user_state_repository import UserCurriculumRepository
from app.modules.grammar.content_repository import get_grammar_content_repository
from app.modules.learning_events.repository import LearningEventRepository
from app.modules.learning_events.service import LearningEventService
from app.modules.users.repository import UserRepository
from app.modules.vocabulary.content_repository import get_vocabulary_content_repository

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


def get_curriculum_service() -> CurriculumService:
    database = get_database()
    curriculum = get_curriculum_content_repository()
    return CurriculumService(
        content=curriculum,
        state_repository=UserCurriculumRepository(database),
        user_repository=UserRepository(database),
        learning_events=LearningEventService(
            repository=LearningEventRepository(database),
            curriculum=curriculum,
            grammar=get_grammar_content_repository(),
            vocabulary=get_vocabulary_content_repository(),
        ),
    )


@router.get("", response_model=CurriculumProgram)
async def get_program(
    _: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[CurriculumService, Depends(get_curriculum_service)],
) -> CurriculumProgram:
    return service.get_program()


@router.get("/stages/{stage_id}", response_model=CurriculumStage)
async def get_stage(
    stage_id: str,
    _: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[CurriculumService, Depends(get_curriculum_service)],
) -> CurriculumStage:
    return service.get_stage(stage_id)


@router.get("/nodes/{node_id}", response_model=CurriculumNode)
async def get_node(
    node_id: str,
    _: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[CurriculumService, Depends(get_curriculum_service)],
) -> CurriculumNode:
    return service.get_node(node_id)


@router.get("/me", response_model=UserCurriculumOverview)
async def get_my_curriculum(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[CurriculumService, Depends(get_curriculum_service)],
) -> UserCurriculumOverview:
    return await run_in_threadpool(service.get_user_curriculum, identity.uid)


@router.post("/me/nodes/{node_id}/start", response_model=UserCurriculumOverview)
async def start_node(
    node_id: str,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[CurriculumService, Depends(get_curriculum_service)],
) -> UserCurriculumOverview:
    return await run_in_threadpool(service.start_node, identity.uid, node_id)
