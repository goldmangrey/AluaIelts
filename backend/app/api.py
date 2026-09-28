from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.modules.users.router import router as users_router
from app.shared.schemas import HealthResponse

api_router = APIRouter()
root_router = APIRouter()
api_router.include_router(users_router)


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
