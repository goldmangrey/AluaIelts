from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.database import get_database
from app.modules.curriculum.content_repository import get_curriculum_content_repository
from app.modules.curriculum.user_state_repository import UserCurriculumRepository
from app.modules.daily_plan.repository import DailyPlanRepository
from app.modules.grammar.content_repository import get_grammar_content_repository
from app.modules.learning_events.repository import LearningEventRepository
from app.modules.mastery.engine import MasteryEngine
from app.modules.mastery.repository import MasteryRepository
from app.modules.mastery.service import MasteryService
from app.modules.progress.engine import ProgressAnalyticsEngine
from app.modules.progress.repository import ProgressAnalyticsRepository
from app.modules.progress.schemas import ProgressSnapshot
from app.modules.progress.service import ProgressAnalyticsService
from app.modules.student_model.service import StudentModelService
from app.modules.users.repository import UserRepository
from app.modules.vocabulary.content_repository import get_vocabulary_content_repository

router = APIRouter(prefix="/progress", tags=["progress"])


def get_progress_service() -> ProgressAnalyticsService:
    database = get_database()
    mastery_repository = MasteryRepository(database)
    users = UserRepository(database)
    vocabulary = get_vocabulary_content_repository()
    grammar = get_grammar_content_repository()
    curriculum = get_curriculum_content_repository()
    mastery_service = MasteryService(
        repository=mastery_repository,
        engine=MasteryEngine(),
        vocabulary=vocabulary,
        grammar=grammar,
    )
    return ProgressAnalyticsService(
        events=LearningEventRepository(database),
        plans=DailyPlanRepository(database),
        mastery_repository=mastery_repository,
        mastery_service=mastery_service,
        student_model=StudentModelService(
            mastery=mastery_repository,
            users=users,
            curriculum_states=UserCurriculumRepository(database),
            curriculum_content=curriculum,
        ),
        users=users,
        vocabulary=vocabulary,
        grammar=grammar,
        engine=ProgressAnalyticsEngine(),
        repository=ProgressAnalyticsRepository(database),
    )


@router.get("", response_model=ProgressSnapshot)
async def get_progress(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ProgressAnalyticsService, Depends(get_progress_service)],
    days: Annotated[int, Query()] = 7,
    timezone: Annotated[str, Query(min_length=1, max_length=100)] = "UTC",
) -> ProgressSnapshot:
    return await run_in_threadpool(service.get_snapshot, identity.uid, days, timezone)
