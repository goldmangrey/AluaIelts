from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.integrations.firebase.firestore import get_firestore_client
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserProfileResponse, UserProfileUpdate
from app.modules.users.service import UserService

router = APIRouter(tags=["users"])


def get_user_service() -> UserService:
    return UserService(UserRepository(get_firestore_client()))


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserProfileResponse:
    profile = await run_in_threadpool(service.get_or_create_profile, identity)
    return UserProfileResponse.from_profile(profile)


@router.patch("/me", response_model=UserProfileResponse)
async def update_me(
    request: UserProfileUpdate,
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserProfileResponse:
    profile = await run_in_threadpool(service.update_profile, identity, request)
    return UserProfileResponse.from_profile(profile)
