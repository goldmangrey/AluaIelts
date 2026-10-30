from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.database import get_database
from app.modules.daily_plan.repository import DailyPlanRepository
from app.modules.exercises.repository import ExerciseRepository
from app.modules.grammar.content_repository import get_grammar_content_repository
from app.modules.partner.repository import PartnerRepository
from app.modules.progress.router import get_progress_service
from app.modules.users.repository import UserRepository
from app.modules.vocabulary_review.lexicon_repository import (
    get_canonical_lexicon_repository,
)
from app.modules.vocabulary_review.repository import VocabularyReviewRepository
from app.modules.vocabulary_review.scheduler import DeterministicVocabularyScheduler
from app.modules.vocabulary_review.service import VocabularyLearningService
from app.modules.widgets.schemas import WidgetSnapshotEnvelope
from app.modules.widgets.service import WidgetSnapshotService

router = APIRouter(prefix="/widgets", tags=["widgets"])


def get_widget_snapshot_service() -> WidgetSnapshotService:
    database = get_database()
    return WidgetSnapshotService(
        users=UserRepository(database),
        plans=DailyPlanRepository(database),
        grammar=get_grammar_content_repository(),
        relationships=PartnerRepository(database),
        progress=get_progress_service(),
        exercises=ExerciseRepository(database),
        vocabulary_learning=VocabularyLearningService(
            repository=VocabularyReviewRepository(database),
            vocabulary=get_canonical_lexicon_repository(),
            scheduler=DeterministicVocabularyScheduler(),
            users=UserRepository(database),
        ),
    )


@router.get("/snapshot", response_model=WidgetSnapshotEnvelope)
async def get_widget_snapshot(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[WidgetSnapshotService, Depends(get_widget_snapshot_service)],
    timezone: Annotated[str, Query(min_length=1, max_length=100)] = "UTC",
) -> WidgetSnapshotEnvelope:
    return await run_in_threadpool(service.get_snapshot, identity.uid, timezone)
