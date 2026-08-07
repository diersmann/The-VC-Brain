"""Collection admin API routes.

Provides endpoints to trigger discovery, check collection health,
and manage identity resolution.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.queue import queue_depth
from app.collectors.registry import all_connectors
from app.db import get_session
from app.db.models import (
    JobRun,
    Observation,
    Opportunity,
    OpportunityFounder,
    Person,
    ScoreSnapshot,
)
from app.job_ledger import create_job, update_job

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


class JobStatusResponse(BaseModel):
    id: str
    job_type: str
    status: str
    phase: str
    attempt: int
    progress: float
    last_error: str | None = None
    result: dict[str, object] | None = None
    cancel_requested: bool
    updated_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


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


class ResearchBatchRequest(BaseModel):
    candidate_ids: list[str] | None = None
    limit: int = 25


class ResearchQueueResponse(BaseModel):
    queued: int
    candidate_ids: list[str]
    job_ids: list[str] = Field(default_factory=list)
    message: str


class ResearchStatusResponse(BaseModel):
    candidate_id: str
    status: str
    research_observations: int
    latest_scores: dict[str, object] | None = None
    scored_at: str | None = None


class AvatarBatchRequest(BaseModel):
    candidate_ids: list[str] | None = None
    limit: int = 100
    force: bool = False


class AvatarQueueResponse(BaseModel):
    queued: int
    candidate_ids: list[str]
    message: str


async def _current_opportunity(session: AsyncSession, person_id: uuid.UUID) -> Opportunity | None:
    result = await session.execute(
        select(Opportunity)
        .join(OpportunityFounder, OpportunityFounder.opportunity_id == Opportunity.id)
        .where(OpportunityFounder.person_id == person_id)
        .order_by(Opportunity.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


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
    session: Annotated[AsyncSession, Depends(get_session)],
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

    job = await create_job(session, "discover")
    await session.commit()

    # Enqueue as a discovery task
    from app.collectors.queue import enqueue as queue_enqueue

    task = {
        "job_type": "discover",
        "query": body.query,
        "source": body.source,
        "job_id": str(job.id),
    }
    try:
        await queue_enqueue(redis, task, priority=10.0)
    except Exception as exc:
        await update_job(
            session,
            job.id,
            status="failed",
            phase="queue",
            last_error=str(exc),
            result={"error": "queue_failed"},
        )
        await session.commit()
        raise HTTPException(status_code=503, detail="Unable to queue discovery job") from exc

    logger.info("discover_triggered", query=body.query, source=body.source)
    msg = f"Discovery enqueued for source={body.source} query={body.query}"
    return DiscoverResponse(job_id=str(job.id), message=msg)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> JobStatusResponse:
    """Return durable status for a queued or completed asynchronous job."""
    job = await session.get(JobRun, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        id=str(job.id),
        job_type=job.job_type,
        status=job.status,
        phase=job.phase,
        attempt=job.attempt,
        progress=job.progress,
        last_error=job.last_error,
        result=job.result,
        cancel_requested=job.cancel_requested,
        updated_at=job.updated_at.isoformat() if job.updated_at else None,
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
    )


@router.get("/health", response_model=HealthResponse)
async def collection_health(
    redis: Annotated[Any, Depends(get_redis)],
) -> HealthResponse:
    """Return collection system health: queue depth and connector status."""
    depths = await queue_depth(redis)
    connectors = {name: "registered" for name in all_connectors()}
    return HealthResponse(queue_depth=depths, connectors=connectors)


# ---------------------------------------------------------------------------
# Tavily multi-axis candidate research
# ---------------------------------------------------------------------------


@router.post("/avatars/batch", response_model=AvatarQueueResponse)
async def fetch_candidate_avatars(
    body: AvatarBatchRequest,
    redis: Annotated[Any, Depends(get_redis)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AvatarQueueResponse:
    """Queue one-time avatar caching for verified, scored candidates."""
    query = (
        select(Person)
        .join(ScoreSnapshot, ScoreSnapshot.subject_id == Person.id)
        .where(
            Person.canonical.is_(True),
            ScoreSnapshot.rubric_version == "founder-tavily-v1",
        )
        .distinct()
        .order_by(Person.created_at.desc())
    )
    if body.candidate_ids:
        try:
            candidate_ids = [uuid.UUID(item) for item in body.candidate_ids]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid candidate id") from exc
        query = query.where(Person.id.in_(candidate_ids))
    if not body.force:
        query = query.where(Person.avatar_data.is_(None))

    result = await session.execute(query.limit(max(1, min(body.limit, 200))))
    people = list(result.scalars().all())

    from app.collectors.queue import enqueue as queue_enqueue

    queued_ids: list[str] = []
    for person in people:
        opportunity = await _current_opportunity(session, person.id)
        if opportunity is None:
            continue
        await queue_enqueue(
            redis,
            {
                "job_type": "fetch_candidate_avatar",
                "person_id": str(person.id),
                "source": "avatar",
            },
            priority=10.0,
        )
        queued_ids.append(str(person.id))

    return AvatarQueueResponse(
        queued=len(queued_ids),
        candidate_ids=queued_ids,
        message=f"Queued avatar caching for {len(queued_ids)} candidates",
    )


@router.post("/research/batch", response_model=ResearchQueueResponse)
async def research_candidates(
    body: ResearchBatchRequest,
    redis: Annotated[Any, Depends(get_redis)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ResearchQueueResponse:
    """Queue Tavily Founder, Market and Idea-Market research for candidates."""
    limit = max(1, min(100, body.limit))
    query = select(Person).where(Person.canonical.is_(True)).order_by(Person.created_at.desc())
    if body.candidate_ids:
        try:
            ids = [uuid.UUID(item) for item in body.candidate_ids]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid candidate id") from exc
        query = query.where(Person.id.in_(ids))

    result = await session.execute(query.limit(200))
    people = list(result.scalars().all())
    if not body.candidate_ids:
        people = [
            person
            for person in people
            if person.display_name
            and person.display_name.lower()
            not in {value.lower() for value in (person.handles or {}).values()}
        ]
    people = people[:limit]

    from app.collectors.queue import enqueue as queue_enqueue

    queued_ids: list[str] = []
    queued_jobs: list[tuple[str, dict[str, Any], Any]] = []
    for person in people:
        opportunity = await _current_opportunity(session, person.id)
        if opportunity is None:
            continue
        job = await create_job(session, "research_candidate")
        queued_jobs.append(
            (
                str(person.id),
                {
                    "job_type": "research_candidate",
                    "person_id": str(person.id),
                    "opportunity_id": str(opportunity.id),
                    "source": "tavily_search",
                    "job_id": str(job.id),
                },
                job,
            )
        )
    await session.commit()

    queued_jobs_ok: list[Any] = []
    for person_id, task, job in queued_jobs:
        try:
            await queue_enqueue(redis, task, priority=10.0)
        except Exception as exc:
            await update_job(
                session,
                job.id,
                status="failed",
                phase="queue",
                last_error=str(exc),
                result={"error": "queue_failed"},
            )
            continue
        queued_ids.append(person_id)
        queued_jobs_ok.append(job)
    await session.commit()

    return ResearchQueueResponse(
        queued=len(queued_ids),
        candidate_ids=queued_ids,
        job_ids=[str(job.id) for job in queued_jobs_ok],
        message=f"Queued Tavily multi-axis research for {len(queued_ids)} candidates",
    )


@router.post("/research/{candidate_id}", response_model=ResearchQueueResponse)
async def research_candidate(
    candidate_id: uuid.UUID,
    redis: Annotated[Any, Depends(get_redis)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ResearchQueueResponse:
    person = await session.get(Person, candidate_id)
    if person is None or not person.canonical:
        raise HTTPException(status_code=404, detail="Candidate not found")
    opportunity = await _current_opportunity(session, person.id)
    if opportunity is None:
        raise HTTPException(status_code=409, detail="Candidate has no opportunity to research")

    from app.collectors.queue import enqueue as queue_enqueue

    job = await create_job(session, "research_candidate")
    await session.commit()
    try:
        await queue_enqueue(
            redis,
            {
                "job_type": "research_candidate",
                "person_id": str(person.id),
                "opportunity_id": str(opportunity.id),
                "source": "tavily_search",
                "job_id": str(job.id),
            },
            priority=10.0,
        )
    except Exception as exc:
        await update_job(
            session,
            job.id,
            status="failed",
            phase="queue",
            last_error=str(exc),
            result={"error": "queue_failed"},
        )
        await session.commit()
        raise HTTPException(status_code=503, detail="Unable to queue research job") from exc
    return ResearchQueueResponse(
        queued=1,
        candidate_ids=[str(person.id)],
        job_ids=[str(job.id)],
        message="Queued Tavily multi-axis research",
    )


@router.get("/research/{candidate_id}/status", response_model=ResearchStatusResponse)
async def candidate_research_status(
    candidate_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ResearchStatusResponse:
    person = await session.get(Person, candidate_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    opportunity = await _current_opportunity(session, person.id)

    snapshot = None
    if opportunity is not None:
        score_result = await session.execute(
            select(ScoreSnapshot)
            .where(
                ScoreSnapshot.subject_id == opportunity.id,
                ScoreSnapshot.subject_type == "opportunity",
                ScoreSnapshot.rubric_version == "opportunity-axes-v1",
            )
            .order_by(ScoreSnapshot.created_at.desc())
            .limit(1)
        )
        snapshot = score_result.scalar_one_or_none()
    count_result = await session.execute(
        select(func.count(Observation.id)).where(
            Observation.subject_id == candidate_id,
            Observation.predicate.like("research_%"),
        )
    )
    observation_count = int(count_result.scalar_one())

    return ResearchStatusResponse(
        candidate_id=str(candidate_id),
        status="completed" if snapshot else "pending" if observation_count else "not_started",
        research_observations=observation_count,
        latest_scores=snapshot.components if snapshot else None,
        scored_at=snapshot.created_at.isoformat() if snapshot and snapshot.created_at else None,
    )


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
    from app.db import session_context
    from app.db.models import PersonMatch

    async with session_context() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(PersonMatch)
            .where(PersonMatch.status == "pending")
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
@router.post("/identity/matches/{match_id}/approve", response_model=PersonMatchActionResponse)
async def approve_match(match_id: str) -> PersonMatchActionResponse:
    """Approve a PersonMatch and merge the two persons."""
    from app.db import session_context
    from app.db.models import Person, PersonMatch
    from app.identity.merge import merge_persons

    async with session_context() as session:
        from sqlalchemy import select

        result = await session.execute(select(PersonMatch).where(PersonMatch.id == match_id))
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
@router.post("/identity/matches/{match_id}/reject", response_model=PersonMatchActionResponse)
async def reject_match(match_id: str) -> PersonMatchActionResponse:
    """Reject a PersonMatch (persons are not the same)."""
    from app.db import session_context
    from app.db.models import PersonMatch

    async with session_context() as session:
        from sqlalchemy import select

        result = await session.execute(select(PersonMatch).where(PersonMatch.id == match_id))
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
# ---------------------------------------------------------------------------
# Multi-agent scoring routes
# ---------------------------------------------------------------------------


@router.post("/research/{candidate_id}/score", response_model=DiscoverResponse)
async def score_candidate_route(
    candidate_id: uuid.UUID,
    redis: Annotated[Any, Depends(get_redis)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DiscoverResponse:
    """Queue multi-agent scoring for a candidate."""
    person = await session.get(Person, candidate_id)
    if person is None or not person.canonical:
        raise HTTPException(status_code=404, detail="Candidate not found")

    from app.collectors.queue import enqueue as queue_enqueue

    job = await create_job(session, "score_candidate")
    await session.commit()
    try:
        await queue_enqueue(
            redis,
            {
                "job_type": "score_candidate",
                "person_id": str(person.id),
                "job_id": str(job.id),
            },
            priority=10.0,
        )
    except Exception as exc:
        await update_job(
            session,
            job.id,
            status="failed",
            phase="queue",
            last_error=str(exc),
            result={"error": "queue_failed"},
        )
        await session.commit()
        raise HTTPException(status_code=503, detail="Unable to queue scoring job") from exc
    return DiscoverResponse(
        job_id=str(job.id), message=f"Queued multi-agent scoring for {candidate_id}"
    )


@router.post("/research/score/batch", response_model=ResearchQueueResponse)
async def score_candidates_batch(
    redis: Annotated[Any, Depends(get_redis)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = 20,
) -> ResearchQueueResponse:
    """Queue multi-agent scoring for all canonical persons with observations."""
    from app.collectors.queue import enqueue as queue_enqueue

    result = await session.execute(
        select(Person.id).where(Person.canonical.is_(True)).limit(limit)
    )
    person_ids = [str(row[0]) for row in result.all()]

    jobs = [await create_job(session, "score_candidate") for _pid in person_ids]
    await session.commit()

    queued_ids: list[str] = []
    queued_jobs: list[Any] = []
    for pid, job in zip(person_ids, jobs, strict=True):
        try:
            await queue_enqueue(
                redis,
                {"job_type": "score_candidate", "person_id": pid, "job_id": str(job.id)},
                priority=5.0,
            )
        except Exception as exc:
            await update_job(
                session,
                job.id,
                status="failed",
                phase="queue",
                last_error=str(exc),
                result={"error": "queue_failed"},
            )
            continue
        queued_ids.append(pid)
        queued_jobs.append(job)
    await session.commit()

    return ResearchQueueResponse(
        queued=len(queued_ids),
        candidate_ids=queued_ids,
        job_ids=[str(job.id) for job in queued_jobs],
        message=f"Queued multi-agent scoring for {len(queued_ids)} candidates",
    )


# ---------------------------------------------------------------------------
# Processing pipeline routes
# ---------------------------------------------------------------------------


@router.post("/research/{candidate_id}/process", response_model=DiscoverResponse)
async def process_candidate_route(
    candidate_id: uuid.UUID,
    redis: Annotated[Any, Depends(get_redis)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DiscoverResponse:
    """Queue the processing pipeline (reconcile + embed + dedup) for a candidate."""
    person = await session.get(Person, candidate_id)
    if person is None or not person.canonical:
        raise HTTPException(status_code=404, detail="Candidate not found")

    from app.collectors.queue import enqueue as queue_enqueue

    await queue_enqueue(
        redis,
        {"job_type": "process_candidate", "person_id": str(person.id)},
        priority=5.0,
    )
    return DiscoverResponse(message=f"Queued processing pipeline for {candidate_id}")
