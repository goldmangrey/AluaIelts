from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import get_settings
from app.db.database import get_database
from app.modules.ai_progress.context_builder import AIProgressContextBuilder
from app.modules.ai_progress.openai_provider import OpenAIProgressProvider
from app.modules.ai_progress.repository import AIProgressRepository
from app.modules.ai_progress.schemas import (
    AIProgressChatResponse,
    AIProgressConversationResponse,
    AIProgressMessageRequest,
    AIProgressPeriodRequest,
    AIProgressReportResponse,
)
from app.modules.ai_progress.service import AIProgressService
from app.modules.curriculum.content_repository import get_curriculum_content_repository
from app.modules.curriculum.user_state_repository import UserCurriculumRepository
from app.modules.daily_plan.repository import DailyPlanRepository
from app.modules.mastery.repository import MasteryRepository
from app.modules.partner.repository import PartnerRepository
from app.modules.progress.router import get_progress_service
from app.modules.student_model.service import StudentModelService
from app.modules.users.repository import UserRepository

router = APIRouter(prefix="/partner/ai-analysis", tags=["partner-ai-analysis"])


def get_ai_progress_service() -> AIProgressService:
    database = get_database()
    users = UserRepository(database)
    mastery = MasteryRepository(database)
    settings = get_settings()
    return AIProgressService(
        relationships=PartnerRepository(database),
        repository=AIProgressRepository(database),
        context_builder=AIProgressContextBuilder(
            progress=get_progress_service(),
            student_model=StudentModelService(
                mastery=mastery,
                users=users,
                curriculum_states=UserCurriculumRepository(database),
                curriculum_content=get_curriculum_content_repository(),
            ),
            plans=DailyPlanRepository(database),
        ),
        provider=OpenAIProgressProvider(settings),
        settings=settings,
    )


@router.post("/report", response_model=AIProgressReportResponse)
async def generate_report(
    request: AIProgressPeriodRequest,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[AIProgressService, Depends(get_ai_progress_service)],
) -> AIProgressReportResponse:
    return await run_in_threadpool(
        service.generate_report,
        identity.uid,
        request.days,
        request.timezone,
        request.language,
    )


@router.post("/conversations", response_model=AIProgressConversationResponse)
async def create_conversation(
    request: AIProgressPeriodRequest,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[AIProgressService, Depends(get_ai_progress_service)],
) -> AIProgressConversationResponse:
    return await run_in_threadpool(
        service.create_conversation,
        identity.uid,
        request.days,
        request.timezone,
        request.language,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=AIProgressConversationResponse,
)
async def get_conversation(
    conversation_id: str,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[AIProgressService, Depends(get_ai_progress_service)],
) -> AIProgressConversationResponse:
    return await run_in_threadpool(service.get_conversation, identity.uid, conversation_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=AIProgressChatResponse,
)
async def send_message(
    conversation_id: str,
    request: AIProgressMessageRequest,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[AIProgressService, Depends(get_ai_progress_service)],
) -> AIProgressChatResponse:
    return await run_in_threadpool(
        service.send_message, identity.uid, conversation_id, request.message
    )
