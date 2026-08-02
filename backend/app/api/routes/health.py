from collections.abc import Awaitable, Callable
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import Settings, get_settings
from app.db import get_engine
from app.storage import check_health as check_storage_health

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    dependencies: dict[str, Literal["ok"]]


async def _check_postgres() -> None:
    engine: AsyncEngine = get_engine()
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def _check_redis() -> None:
    import redis.asyncio as aioredis

    redis = aioredis.from_url(get_settings().redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
    try:
        await redis.ping()
        if not await redis.exists("vcbrain:worker:heartbeat"):
            raise RuntimeError("worker heartbeat is missing")
    finally:
        await redis.aclose()


async def _check_storage() -> None:
    await check_storage_health()


async def _run_check(
    name: str,
    check: Callable[[], Awaitable[None]],
    checks: dict[str, Literal["ok"]],
    failures: list[str],
) -> None:
    try:
        await check()
        checks[name] = "ok"
    except Exception:
        failures.append(name)


@router.get("/health", response_model=HealthResponse)
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(status="ok", service=settings.name)


@router.get("/ready", response_model=ReadinessResponse)
async def readiness() -> ReadinessResponse:
    checks: dict[str, Literal["ok"]] = {}
    failures: list[str] = []

    await _run_check("postgres", _check_postgres, checks, failures)
    await _run_check("redis", _check_redis, checks, failures)
    await _run_check("minio", _check_storage, checks, failures)

    if failures:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "failed_dependencies": failures},
        )

    return ReadinessResponse(status="ready", dependencies=checks)
