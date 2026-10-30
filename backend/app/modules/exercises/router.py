from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import get_settings
from app.db.database import get_database
from app.modules.curriculum.content_repository import get_curriculum_content_repository
from app.modules.curriculum.service import CurriculumService
from app.modules.curriculum.user_state_repository import UserCurriculumRepository
from app.modules.daily_plan.engine import DailyPlanEngine
from app.modules.daily_plan.repository import DailyPlanRepository
from app.modules.daily_plan.service import DailyPlanService
from app.modules.exercises.ai_generator import OpenAIExerciseGenerator
from app.modules.exercises.ai_validator import AIExerciseValidator
from app.modules.exercises.coordinator import ExerciseGenerationCoordinator
from app.modules.exercises.generator import DeterministicExerciseGenerator
from app.modules.exercises.grader import ExerciseGrader
from app.modules.exercises.repository import ExerciseRepository
from app.modules.exercises.schemas import (
    CreateExerciseSessionRequest,
    ExerciseAttemptResult,
    ExerciseSessionResponse,
    SubmitExerciseAttemptRequest,
)
from app.modules.exercises.service import ExerciseService
from app.modules.grammar.content_repository import get_grammar_content_repository
from app.modules.learning_events.repository import LearningEventRepository
from app.modules.learning_events.service import LearningEventService
from app.modules.mastery.engine import MasteryEngine
from app.modules.mastery.repository import MasteryRepository
from app.modules.mastery.service import MasteryService
from app.modules.users.repository import UserRepository
from app.modules.vocabulary.content_repository import get_vocabulary_content_repository
from app.modules.vocabulary_review.lexicon_repository import get_canonical_lexicon_repository
from app.modules.vocabulary_review.repository import VocabularyReviewRepository
from app.modules.vocabulary_review.scheduler import DeterministicVocabularyScheduler
from app.modules.vocabulary_review.service import VocabularyLearningService

router = APIRouter(prefix="/exercise-sessions", tags=["exercise-sessions"])


def get_exercise_service() -> ExerciseService:
    database = get_database()
    curriculum_content = get_curriculum_content_repository()
    vocabulary = get_vocabulary_content_repository()
    grammar = get_grammar_content_repository()
    users = UserRepository(database)
    events = LearningEventService(
        repository=LearningEventRepository(database),
        curriculum=curriculum_content,
        grammar=grammar,
        vocabulary=vocabulary,
    )
    curriculum = CurriculumService(
        content=curriculum_content,
        state_repository=UserCurriculumRepository(database),
        user_repository=users,
        learning_events=events,
    )
    mastery_repository = MasteryRepository(database)
    mastery = MasteryService(
        repository=mastery_repository,
        engine=MasteryEngine(),
        vocabulary=vocabulary,
        grammar=grammar,
    )
    plans = DailyPlanRepository(database)
    daily_plans = DailyPlanService(
        repository=plans,
        engine=DailyPlanEngine(),
        curriculum=curriculum,
        users=users,
        mastery=mastery_repository,
        grammar=grammar,
        vocabulary_learning=VocabularyLearningService(
            repository=VocabularyReviewRepository(database),
            vocabulary=get_canonical_lexicon_repository(),
            scheduler=DeterministicVocabularyScheduler(),
            users=UserRepository(database),
        ),
    )
    return ExerciseService(
        repository=ExerciseRepository(database),
        plans=plans,
        daily_plan_service=daily_plans,
        generator=ExerciseGenerationCoordinator(
            deterministic=DeterministicExerciseGenerator(vocabulary, grammar, curriculum_content),
            ai=OpenAIExerciseGenerator(get_settings()),
            validator=AIExerciseValidator(),
            vocabulary=vocabulary,
            grammar=grammar,
            settings=get_settings(),
        ),
        grader=ExerciseGrader(),
        events=events,
        mastery=mastery,
        mastery_repository=mastery_repository,
    )


@router.post("", response_model=ExerciseSessionResponse)
async def create_session(
    request: CreateExerciseSessionRequest,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ExerciseService, Depends(get_exercise_service)],
) -> ExerciseSessionResponse:
    return await run_in_threadpool(
        service.create_session, identity.uid, request.local_date, request.daily_plan_item_id
    )


@router.get("/{session_id}", response_model=ExerciseSessionResponse)
async def get_session(
    session_id: str,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ExerciseService, Depends(get_exercise_service)],
) -> ExerciseSessionResponse:
    return await run_in_threadpool(service.get_session, identity.uid, session_id)


@router.post(
    "/{session_id}/exercises/{exercise_id}/attempts",
    response_model=ExerciseAttemptResult,
)
async def submit_attempt(
    session_id: str,
    exercise_id: str,
    request: SubmitExerciseAttemptRequest,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[ExerciseService, Depends(get_exercise_service)],
) -> ExerciseAttemptResult:
    return await run_in_threadpool(
        service.submit_attempt, identity.uid, session_id, exercise_id, request
    )
