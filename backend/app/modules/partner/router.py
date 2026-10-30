from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.database import get_database
from app.modules.curriculum.content_repository import get_curriculum_content_repository
from app.modules.curriculum.user_state_repository import UserCurriculumRepository
from app.modules.daily_plan.repository import DailyPlanRepository
from app.modules.mastery.repository import MasteryRepository
from app.modules.partner.models import PartnerSharingSettings
from app.modules.partner.repository import PartnerRepository
from app.modules.partner.schemas import (
    AcceptPartnerInviteRequest,
    PartnerDashboardSnapshot,
    PartnerInviteResponse,
    PartnerStatusResponse,
)
from app.modules.partner.service import PartnerService
from app.modules.progress.router import get_progress_service
from app.modules.student_model.service import StudentModelService
from app.modules.users.repository import UserRepository

router = APIRouter(prefix="/partner", tags=["partner"])


def get_partner_service() -> PartnerService:
    database = get_database()
    users = UserRepository(database)
    mastery = MasteryRepository(database)
    return PartnerService(
        repository=PartnerRepository(database),
        users=users,
        plans=DailyPlanRepository(database),
        progress=get_progress_service(),
        student_model=StudentModelService(
            mastery=mastery,
            users=users,
            curriculum_states=UserCurriculumRepository(database),
            curriculum_content=get_curriculum_content_repository(),
        ),
    )


@router.get("/status", response_model=PartnerStatusResponse)
async def get_status(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[PartnerService, Depends(get_partner_service)],
) -> PartnerStatusResponse:
    return await run_in_threadpool(service.get_status, identity.uid)


@router.post("/invitations", response_model=PartnerInviteResponse)
async def create_invite(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[PartnerService, Depends(get_partner_service)],
) -> PartnerInviteResponse:
    return await run_in_threadpool(service.create_invite, identity.uid)


@router.post("/invitations/accept", response_model=PartnerStatusResponse)
async def accept_invite(
    request: AcceptPartnerInviteRequest,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[PartnerService, Depends(get_partner_service)],
) -> PartnerStatusResponse:
    await run_in_threadpool(service.accept_invite, identity.uid, request.code)
    return await run_in_threadpool(service.get_status, identity.uid)


@router.patch("/sharing", response_model=PartnerStatusResponse)
async def update_sharing(
    settings: PartnerSharingSettings,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[PartnerService, Depends(get_partner_service)],
) -> PartnerStatusResponse:
    return await run_in_threadpool(service.update_sharing, identity.uid, settings)


@router.post("/relationship/revoke", response_model=PartnerStatusResponse)
async def revoke_relationship(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[PartnerService, Depends(get_partner_service)],
) -> PartnerStatusResponse:
    return await run_in_threadpool(service.revoke, identity.uid)


@router.get("/dashboard", response_model=PartnerDashboardSnapshot)
async def get_dashboard(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[PartnerService, Depends(get_partner_service)],
    days: Annotated[int, Query()] = 7,
    timezone: Annotated[str, Query(min_length=1, max_length=100)] = "UTC",
) -> PartnerDashboardSnapshot:
    return await run_in_threadpool(service.get_dashboard, identity.uid, days, timezone)
