from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.database import get_database
from app.modules.curriculum.content_repository import get_curriculum_content_repository
from app.modules.curriculum.user_state_repository import UserCurriculumRepository
from app.modules.mastery.repository import MasteryRepository
from app.modules.student_model.models import StudentModelSnapshot
from app.modules.student_model.service import StudentModelService
from app.modules.users.repository import UserRepository

router = APIRouter(prefix="/student-model", tags=["student-model"])


def get_student_model_service() -> StudentModelService:
    client = get_database()
    return StudentModelService(
        mastery=MasteryRepository(client),
        users=UserRepository(client),
        curriculum_states=UserCurriculumRepository(client),
        curriculum_content=get_curriculum_content_repository(),
    )


@router.get("", response_model=StudentModelSnapshot)
async def get_student_model(
    identity: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[StudentModelService, Depends(get_student_model_service)],
) -> StudentModelSnapshot:
    return await run_in_threadpool(service.get_snapshot, identity.uid)
