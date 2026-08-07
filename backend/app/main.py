from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import get_settings
from app.db import get_engine
from app.logging import configure_logging
from app.request_context import RequestContextMiddleware
from app.storage import close_client


async def _unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    """Return a generic error while leaving a PII-free correlation trail."""
    request_id = getattr(request.state, "request_id", "unknown")
    structlog.get_logger("app").error(
        "unhandled_request_error",
        request_id=request_id,
        error_type=type(exc).__name__,
    )
    response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
    if request_id != "unknown":
        response.headers["X-Request-ID"] = request_id
    return response


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    structlog.get_logger().info("application_started")
    try:
        yield
    finally:
        await close_client()
        await get_engine().dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.name, version="0.1.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    application.add_middleware(RequestContextMiddleware)
    application.add_exception_handler(Exception, _unhandled_exception)
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
