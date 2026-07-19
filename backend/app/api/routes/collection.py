"""Collection admin API routes.

Provides endpoints to trigger discovery, check collection health,
and manage identity resolution.
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


class IdentityResolveResponse(BaseModel):
    message: str


class PersonMatchResponse(BaseModel):
    id: str
    person_a_id: str
    person_b_id: str
    confidence: float
    reasons: dict[str, object] | None
    status: str
    created_at: str | None = None


class PersonMatchListResponse(BaseModel):
    matches: list[PersonMatchResponse]


class PersonMatchActionResponse(BaseModel):
    message: str


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


# ---------------------------------------------------------------------------
# Identity resolution routes
# ---------------------------------------------------------------------------


@router.post("/identity/resolve", response_model=IdentityResolveResponse)
async def trigger_identity_resolve(
    redis: Annotated[Any, Depends(get_redis)],
) -> IdentityResolveResponse:
    """Manually trigger identity resolution.

    Enqueues a resolve_identities_job via the Arq pool.
    """
    from app.collectors.queue import enqueue as queue_enqueue

    task = {
        "job_type": "resolve_identities",
    }
    await queue_enqueue(redis, task, priority=10.0)

    logger.info("identity_resolve_triggered")
    return IdentityResolveResponse(message="Identity resolution enqueued")


@router.get("/identity/matches", response_model=PersonMatchListResponse)
async def list_pending_matches() -> PersonMatchListResponse:
    """List all pending PersonMatch records for review."""
    from app.db import get_session
    from app.db.models import PersonMatch

    session = await get_session()
    try:
        from sqlalchemy import select

        result = await session.execute(
            select(PersonMatch).where(PersonMatch.status == "pending")
            .order_by(PersonMatch.confidence.desc())
        )
        matches = result.scalars().all()

        return PersonMatchListResponse(
            matches=[
                PersonMatchResponse(
                    id=str(m.id),
                    person_a_id=str(m.person_a_id),
                    person_b_id=str(m.person_b_id),
                    confidence=m.confidence,
                    reasons=m.reasons,
                    status=m.status,
                    created_at=m.created_at.isoformat() if m.created_at else None,
                )
                for m in matches
            ]
        )
    finally:
        await session.close()


@router.post("/identity/matches/{match_id}/approve", response_model=PersonMatchActionResponse)
async def approve_match(match_id: str) -> PersonMatchActionResponse:
    """Approve a PersonMatch and merge the two persons."""
    from app.db import get_session
    from app.db.models import Person, PersonMatch
    from app.identity.merge import merge_persons

    session = await get_session()
    try:
        from sqlalchemy import select

        result = await session.execute(
            select(PersonMatch).where(PersonMatch.id == match_id)
        )
        match = result.scalar_one_or_none()
        if match is None:
            raise HTTPException(status_code=404, detail="Match not found")

        if match.status != "pending":
            raise HTTPException(status_code=400, detail=f"Match already {match.status}")

        # Pick canonical (earlier created)
        person_a = await session.get(Person, match.person_a_id)
        person_b = await session.get(Person, match.person_b_id)
        if not person_a or not person_b:
            raise HTTPException(status_code=404, detail="One or both persons not found")

        reasons_raw = match.reasons.get("reasons", []) if match.reasons else []
        if isinstance(reasons_raw, list):
            reasons: list[str] = [str(r) for r in reasons_raw]
        else:
            reasons = []
        if person_a.created_at and person_b.created_at:
            if person_a.created_at <= person_b.created_at:
                canonical_id, duplicate_id = match.person_a_id, match.person_b_id
            else:
                canonical_id, duplicate_id = match.person_b_id, match.person_a_id
        else:
            canonical_id, duplicate_id = match.person_a_id, match.person_b_id

        await merge_persons(session, canonical_id, duplicate_id, match.confidence, reasons)

        match.status = "approved"
        match.resolved_by = "api"
        from datetime import UTC, datetime
        match.resolved_at = datetime.now(UTC)

        await session.commit()

        logger.info(
            "identity_match_approved",
            match_id=match_id,
            canonical=str(canonical_id),
            duplicate=str(duplicate_id),
        )
        return PersonMatchActionResponse(message="Match approved and persons merged")
    finally:
        await session.close()


@router.post("/identity/matches/{match_id}/reject", response_model=PersonMatchActionResponse)
async def reject_match(match_id: str) -> PersonMatchActionResponse:
    """Reject a PersonMatch (persons are not the same)."""
    from app.db import get_session
    from app.db.models import PersonMatch

    session = await get_session()
    try:
        from sqlalchemy import select

        result = await session.execute(
            select(PersonMatch).where(PersonMatch.id == match_id)
        )
        match = result.scalar_one_or_none()
        if match is None:
            raise HTTPException(status_code=404, detail="Match not found")

        if match.status != "pending":
            raise HTTPException(status_code=400, detail=f"Match already {match.status}")

        match.status = "rejected"
        match.resolved_by = "api"
        from datetime import UTC, datetime
        match.resolved_at = datetime.now(UTC)

        await session.commit()

        logger.info("identity_match_rejected", match_id=match_id)
        return PersonMatchActionResponse(message="Match rejected")
    finally:
        await session.close()
