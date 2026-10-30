from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.database import get_database
from app.modules.users.repository import UserRepository
from app.modules.vocabulary_review.lexicon_repository import (
    get_canonical_lexicon_repository,
)
from app.modules.vocabulary_review.repository import VocabularyReviewRepository
from app.modules.vocabulary_review.scheduler import DeterministicVocabularyScheduler
from app.modules.vocabulary_review.schemas import (
    SubmitReviewResponseRequest,
    SubmitReviewResponseResult,
    VocabularyLearningTodayResponse,
    VocabularyReviewSessionResponse,
    WeeklyReviewResponse,
)
from app.modules.vocabulary_review.service import VocabularyLearningService

router = APIRouter(prefix="/vocabulary-learning", tags=["vocabulary-learning"])


def get_vocabulary_learning_service() -> VocabularyLearningService:
    database = get_database()
    return VocabularyLearningService(
        repository=VocabularyReviewRepository(database),
        vocabulary=get_canonical_lexicon_repository(),
        scheduler=DeterministicVocabularyScheduler(),
        users=UserRepository(database),
    )


@router.get("/today", response_model=VocabularyLearningTodayResponse)
async def get_today(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[VocabularyLearningService, Depends(get_vocabulary_learning_service)],
    timezone: Annotated[str, Query(min_length=1, max_length=100)] = "UTC",
) -> VocabularyLearningTodayResponse:
    return await run_in_threadpool(service.get_today, identity.uid, timezone)


@router.get("/review-sessions/{session_id}", response_model=VocabularyReviewSessionResponse)
async def get_review_session(
    session_id: str,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[VocabularyLearningService, Depends(get_vocabulary_learning_service)],
) -> VocabularyReviewSessionResponse:
    return await run_in_threadpool(service.get_session, identity.uid, session_id)


@router.post(
    "/review-sessions/{session_id}/responses",
    response_model=SubmitReviewResponseResult,
)
async def submit_review_response(
    session_id: str,
    request: SubmitReviewResponseRequest,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[VocabularyLearningService, Depends(get_vocabulary_learning_service)],
) -> SubmitReviewResponseResult:
    return await run_in_threadpool(service.submit_response, identity.uid, session_id, request)


@router.get("/weekly", response_model=WeeklyReviewResponse)
async def get_weekly(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[VocabularyLearningService, Depends(get_vocabulary_learning_service)],
    timezone: Annotated[str, Query(min_length=1, max_length=100)] = "UTC",
) -> WeeklyReviewResponse:
    return await run_in_threadpool(service.get_weekly, identity.uid, timezone)
