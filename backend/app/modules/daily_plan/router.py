from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.database import get_database
from app.modules.curriculum.content_repository import get_curriculum_content_repository
from app.modules.curriculum.service import CurriculumService
from app.modules.curriculum.user_state_repository import UserCurriculumRepository
from app.modules.daily_plan.engine import DailyPlanEngine
from app.modules.daily_plan.repository import DailyPlanRepository
from app.modules.daily_plan.schemas import DailyPlanResponse, EnsureDailyPlanRequest
from app.modules.daily_plan.service import DailyPlanService
from app.modules.grammar.content_repository import get_grammar_content_repository
from app.modules.learning_events.repository import LearningEventRepository
from app.modules.learning_events.service import LearningEventService
from app.modules.mastery.repository import MasteryRepository
from app.modules.users.repository import UserRepository
from app.modules.vocabulary.content_repository import get_vocabulary_content_repository
from app.modules.vocabulary_review.lexicon_repository import get_canonical_lexicon_repository
from app.modules.vocabulary_review.repository import VocabularyReviewRepository
from app.modules.vocabulary_review.scheduler import DeterministicVocabularyScheduler
from app.modules.vocabulary_review.service import VocabularyLearningService

router = APIRouter(prefix="/daily-plans", tags=["daily-plans"])


def get_daily_plan_service() -> DailyPlanService:
    database = get_database()
    curriculum_content = get_curriculum_content_repository()
    vocabulary = get_vocabulary_content_repository()
    grammar = get_grammar_content_repository()
    users = UserRepository(database)
    curriculum = CurriculumService(
        content=curriculum_content,
        state_repository=UserCurriculumRepository(database),
        user_repository=users,
        learning_events=LearningEventService(
            repository=LearningEventRepository(database),
            curriculum=curriculum_content,
            grammar=grammar,
            vocabulary=vocabulary,
        ),
    )
    return DailyPlanService(
        repository=DailyPlanRepository(database),
        engine=DailyPlanEngine(),
        curriculum=curriculum,
        users=users,
        mastery=MasteryRepository(database),
        grammar=grammar,
        vocabulary_learning=VocabularyLearningService(
            repository=VocabularyReviewRepository(database),
            vocabulary=get_canonical_lexicon_repository(),
            scheduler=DeterministicVocabularyScheduler(),
            users=users,
        ),
    )


@router.post("/today", response_model=DailyPlanResponse)
async def ensure_today_plan(
    request: EnsureDailyPlanRequest,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[DailyPlanService, Depends(get_daily_plan_service)],
) -> DailyPlanResponse:
    return await run_in_threadpool(service.ensure_today, identity.uid, request.timezone)


@router.get("/today", response_model=DailyPlanResponse)
async def get_today_plan(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[DailyPlanService, Depends(get_daily_plan_service)],
    timezone: str = Query(min_length=1, max_length=100),
) -> DailyPlanResponse:
    return await run_in_threadpool(service.get_today, identity.uid, timezone)


@router.get("/{local_date}", response_model=DailyPlanResponse)
async def get_plan(
    local_date: date,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[DailyPlanService, Depends(get_daily_plan_service)],
) -> DailyPlanResponse:
    return await run_in_threadpool(service.get_plan, identity.uid, local_date)
