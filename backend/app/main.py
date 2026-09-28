from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import api_router, root_router
from app.core.config import get_settings
from app.core.exceptions import AluaError
from app.core.logging import configure_logging
from app.core.middleware import configure_middleware
from app.shared.schemas import ErrorDetail, ErrorResponse


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    logger = structlog.get_logger(__name__)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("application_started", environment=settings.environment)
        yield
        logger.info("application_stopped", environment=settings.environment)

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        # Never expose framework tracebacks to API clients, including local environments.
        debug=False,
        lifespan=lifespan,
    )

    @application.exception_handler(AluaError)
    async def alua_error_handler(_: Request, exc: AluaError) -> JSONResponse:
        payload = ErrorResponse(error=ErrorDetail(code=exc.code, message=exc.message))
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @application.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            method=request.method,
            path=request.url.path,
            exc_info=exc,
        )
        payload = ErrorResponse(
            error=ErrorDetail(
                code="internal_server_error",
                message="An unexpected error occurred.",
            )
        )
        return JSONResponse(status_code=500, content=payload.model_dump())

    configure_middleware(application, settings)
    application.include_router(root_router)
    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_app()
