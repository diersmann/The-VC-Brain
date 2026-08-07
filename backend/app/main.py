from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.client_lifecycle import close_clients
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
    return _error_response(
        request,
        status_code=500,
        detail="Internal server error",
    )


_ERROR_MESSAGES: dict[int, str] = {
    400: "The request was invalid.",
    401: "Authentication is required.",
    403: "You do not have permission to perform this request.",
    404: "The requested resource was not found.",
    405: "The request method is not allowed for this resource.",
    409: "The request conflicts with the current resource state.",
    422: "The request could not be validated.",
    408: "The request timed out.",
    429: "Too many requests were received.",
    415: "The request media type is not supported.",
    500: "An internal server error occurred.",
    502: "An upstream service returned an error.",
    503: "The service is temporarily unavailable.",
    504: "The service timed out.",
}


def _error_code(status_code: int) -> str:
    if status_code in {400, 401, 403, 404, 405, 408, 409, 415, 422, 429, 500, 502, 503, 504}:
        return {
            400: "bad_request",
            401: "authentication_required",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
            408: "request_timeout",
            409: "conflict",
            415: "unsupported_media_type",
            422: "validation_error",
            429: "rate_limited",
            500: "internal_server_error",
            502: "bad_gateway",
            503: "service_unavailable",
            504: "gateway_timeout",
        }[status_code]
    if 400 <= status_code < 500:
        return "request_error"
    return "server_error"


def _error_response(
    request: Request,
    *,
    status_code: int,
    detail: object,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Build the v1 error envelope while retaining the legacy ``detail`` key."""
    request_id = getattr(request.state, "request_id", None)
    safe_detail = (
        "Internal server error"
        if status_code == 500
        else "The service is temporarily unavailable."
        if status_code >= 500
        else detail
    )
    error: dict[str, object] = {
        "version": "v1",
        "code": _error_code(status_code),
        "message": _ERROR_MESSAGES.get(
            status_code,
            "The request could not be completed."
            if status_code < 500
            else "The service returned an error.",
        ),
        "retryable": status_code in {408, 425, 429} or status_code >= 500,
    }
    if isinstance(request_id, str) and request_id:
        error["request_id"] = request_id
    response = JSONResponse(
        status_code=status_code,
        content={"version": "v1", "detail": jsonable_encoder(safe_detail), "error": error},
    )
    if headers:
        response.headers.update(headers)
    if isinstance(request_id, str) and request_id:
        response.headers["X-Request-ID"] = request_id
    return response


def _safe_validation_detail(exc: RequestValidationError) -> list[dict[str, object]]:
    """Keep validation locations without echoing submitted values or messages."""
    return [
        {
            "loc": jsonable_encoder(error.get("loc", [])),
            "type": error.get("type", "validation_error"),
            "msg": "The request field is invalid.",
        }
        for error in exc.errors()
    ]


async def _http_exception(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        return _error_response(request, status_code=500, detail="Internal server error")
    return _error_response(
        request,
        status_code=exc.status_code,
        detail=exc.detail,
        headers=exc.headers,
    )


async def _request_validation_exception(
    request: Request, exc: Exception
) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return _error_response(
            request,
            status_code=422,
            detail="The request could not be validated.",
        )
    return _error_response(request, status_code=422, detail=_safe_validation_detail(exc))


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    structlog.get_logger().info("application_started")
    try:
        yield
    finally:
        # Release process-owned providers even if another shutdown hook fails.
        try:
            await close_client()
        finally:
            try:
                await close_clients()
            finally:
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
    application.add_exception_handler(StarletteHTTPException, _http_exception)
    application.add_exception_handler(HTTPException, _http_exception)
    application.add_exception_handler(RequestValidationError, _request_validation_exception)
    application.add_exception_handler(Exception, _unhandled_exception)
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
