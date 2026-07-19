"""Collection admin API routes.

Provides endpoints to trigger discovery and check collection health.
"""

from __future__ import annotations

from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.collectors.queue import queue_depth
from app.collectors.registry import all_connectors

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/collection", tags=["collection"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class DiscoverRequest(BaseModel):
    query: str
    source: str


class DiscoverResponse(BaseModel):
    job_id: str | None = None
    message: str


class HealthResponse(BaseModel):
    queue_depth: dict[str, int]
    connectors: dict[str, str]


# ---------------------------------------------------------------------------
# Redis dependency
# ---------------------------------------------------------------------------


async def get_redis() -> Any:
    """Return a Redis connection (lazy-initialized)."""
    import redis.asyncio as aioredis

    from app.config import get_settings

    settings = get_settings()
    r = aioredis.from_url(settings.redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
    try:
        yield r
    finally:
        await r.aclose()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/discover", response_model=DiscoverResponse)
async def trigger_discover(
    body: DiscoverRequest,
    redis: Annotated[Any, Depends(get_redis)],
) -> DiscoverResponse:
    """Trigger a discovery job for a given source and query.

    The job is enqueued in the Redis priority queue and picked up by
    the dispatcher cron.
    """
    # Validate source
    try:
        from app.collectors.registry import get_connector

        get_connector(body.source)
    except KeyError as err:
        raise HTTPException(status_code=400, detail=f"Unknown source: {body.source}") from err

    # Enqueue as a discovery task
    from app.collectors.queue import enqueue as queue_enqueue

    task = {
        "job_type": "discover",
        "query": body.query,
        "source": body.source,
    }
    await queue_enqueue(redis, task, priority=10.0)

    logger.info("discover_triggered", query=body.query, source=body.source)
    msg = f"Discovery enqueued for source={body.source} query={body.query}"
    return DiscoverResponse(message=msg)


@router.get("/health", response_model=HealthResponse)
async def collection_health(
    redis: Annotated[Any, Depends(get_redis)],
) -> HealthResponse:
    """Return collection system health: queue depth and connector status."""
    depths = await queue_depth(redis)
    connectors = {
        name: "registered" for name in all_connectors()
    }
    return HealthResponse(queue_depth=depths, connectors=connectors)
