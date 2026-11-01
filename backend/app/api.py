from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.modules.ai_progress.router import router as ai_progress_router
from app.modules.curriculum.router import router as curriculum_router
from app.modules.daily_plan.router import router as daily_plan_router
from app.modules.enrollment.router import router as enrollment_router
from app.modules.exercises.router import router as exercises_router
from app.modules.grammar.router import router as grammar_router
from app.modules.learning_events.router import router as learning_events_router
from app.modules.learning_quality.router import router as learning_quality_router
from app.modules.mastery.router import router as mastery_router
from app.modules.partner.router import router as partner_router
from app.modules.progress.router import router as progress_router
from app.modules.reading.router import router as reading_router
from app.modules.registration.router import router as registration_router
from app.modules.student_model.router import router as student_model_router
from app.modules.study.router import router as study_router
from app.modules.users.router import router as users_router
from app.modules.vocabulary.router import router as vocabulary_router
from app.modules.vocabulary_review.router import router as vocabulary_review_router
from app.modules.widgets.router import router as widgets_router
from app.shared.schemas import HealthResponse

api_router = APIRouter()
api_router.include_router(registration_router)
api_router.include_router(reading_router)
api_router.include_router(study_router)
api_router.include_router(learning_quality_router)
root_router = APIRouter()
api_router.include_router(users_router)
api_router.include_router(ai_progress_router)
api_router.include_router(curriculum_router)
api_router.include_router(daily_plan_router)
api_router.include_router(exercises_router)
api_router.include_router(enrollment_router)
api_router.include_router(grammar_router)
api_router.include_router(learning_events_router)
api_router.include_router(mastery_router)
api_router.include_router(partner_router)
api_router.include_router(progress_router)
api_router.include_router(student_model_router)
api_router.include_router(vocabulary_router)
api_router.include_router(vocabulary_review_router)
api_router.include_router(widgets_router)


@api_router.get("/health", response_model=HealthResponse, tags=["system"])
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@root_router.get("/", tags=["system"])
async def root(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {"name": settings.app_name, "version": settings.app_version}
