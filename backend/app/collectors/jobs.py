"""Arq job functions for the data collector.

Jobs:
    discover_job  — runs a connector's discover phase, writes Person stubs
                    + Observations + SignalScore, enqueues deep-collect for
                    persons above threshold.
    collect_job   — runs a connector's collect phase, writes SourceSnapshot
                    to MinIO + Observations.
    dispatcher_job — periodic cron that pops from the Redis priority queue
                     and enqueues Arq jobs.
    recompute_signals_job — periodic cron that re-evaluates signal scores
                            from existing observations.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base import Seed
from app.collectors.priority import info_gain
from app.collectors.priority import priority as compute_priority
from app.collectors.queue import (
    decrement_tavily_budget,
    get_tavily_budget_remaining,
    pop_top,
    queue_depth,
)
from app.collectors.queue import (
    enqueue as queue_enqueue,
)
from app.collectors.registry import get_connector
from app.collectors.signals import above_threshold, compute_signal_score
from app.collectors.signals import (
    arxiv_signal as compute_arxiv_signal,
)
from app.collectors.signals import (
    github_signal as compute_github_signal,
)
from app.collectors.signals import (
    producthunt_signal as compute_producthunt_signal,
)
from app.collectors.signals import web_signal as compute_web_signal
from app.db.models import Observation, Person, ScoreSnapshot, SourceSnapshot
from app.storage import put_snapshot

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Session helper
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _session_ctx(ctx: dict[str, Any]) -> AsyncIterator[AsyncSession]:
    """Create an async DB session from the factory in ctx, close on exit."""
    factory = ctx.get("session_factory")
    if factory is None:
        msg = "session_factory not initialized — did startup() run?"
        raise RuntimeError(msg)
    session: AsyncSession = factory()
    try:
        yield session
    finally:
        await session.close()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_or_create_person(
    session: AsyncSession,
    source_type: str,
    handle: str,
    display_hint: str = "",
) -> Person:
    """Find a Person by handle in the JSONB handles column, or create one."""
    # Try to find existing person with this handle
    result = await session.execute(
        select(Person).where(
            Person.handles[source_type].as_string() == handle
        )
    )
    person = result.scalar_one_or_none()
    if person is not None:
        return person

    # Create new person
    stable_id = f"{source_type}:{handle}"
    person = Person(
        stable_id=stable_id,
        display_name=display_hint or handle,
        handles={source_type: handle},
        consent_state="pending",
    )
    session.add(person)
    await session.flush()
    logger.info("person_created", stable_id=stable_id, source=source_type)
    return person


async def _write_snapshot(
    session: AsyncSession,
    collected: Any,
) -> SourceSnapshot:
    """Store raw content in MinIO and create a SourceSnapshot row."""
    content_hash, storage_path = await put_snapshot(
        content=collected.content,
        content_type=collected.content_type,
        source_type=collected.source_type,
    )

    snapshot = SourceSnapshot(
        uri=collected.uri,
        source_type=collected.source_type,
        content_hash=content_hash,
        storage_path=storage_path,
        license_metadata=collected.license_hint,
        collected_at=datetime.now(UTC),
    )
    session.add(snapshot)
    await session.flush()
    return snapshot


async def _write_observations(
    session: AsyncSession,
    snapshot: SourceSnapshot,
    observations: list[dict[str, object]],
    subject_id: uuid.UUID | None,
) -> None:
    """Write Observation rows linked to a SourceSnapshot."""
    now = datetime.now(UTC)
    for obs in observations:
        # Parse observed_at: connectors may pass an ISO string or a datetime
        raw_observed_at = obs.get("observed_at", now)
        if isinstance(raw_observed_at, str):
            observed_at = datetime.fromisoformat(raw_observed_at)
        elif isinstance(raw_observed_at, datetime):
            observed_at = raw_observed_at
        else:
            observed_at = now

        observation = Observation(
            snapshot_id=snapshot.id,
            subject_id=subject_id,
            predicate=str(obs.get("predicate", "")),
            object_value=str(obs.get("object_value", "")),
            observed_at=observed_at,
            extractor_version=f"{snapshot.source_type}-v1",
            confidence=float(str(obs.get("confidence", 1.0))),
        )
        session.add(observation)
    await session.flush()


async def _compute_and_store_signal(
    session: AsyncSession,
    person: Person,
    source_type: str,
) -> dict[str, float]:
    """Compute a signal score from existing observations and store as ScoreSnapshot."""
    # Fetch all observations for this person
    result = await session.execute(
        select(Observation).where(Observation.subject_id == person.id)
    )
    observations = result.scalars().all()

    # Compute per-source signals from observations
    github_score = 0.0
    producthunt_score = 0.0
    arxiv_score = 0.0
    web_score = 0.0

    for obs in observations:
        pred = obs.predicate
        val = obs.object_value
        if pred == "github_total_stars":
            github_score = compute_github_signal(
                total_stars=int(val) if val.isdigit() else 0
            )
        elif pred == "producthunt_total_upvotes":
            producthunt_score = compute_producthunt_signal(
                total_upvotes=int(val) if val.isdigit() else 0
            )
        elif pred == "arxiv_total_citations":
            arxiv_score = compute_arxiv_signal(
                total_citations=int(val) if val.isdigit() else 0
            )
        elif pred == "page_content":
            web_score = compute_web_signal(has_company_site=True)

    components = compute_signal_score(
        github=github_score,
        producthunt=producthunt_score,
        arxiv=arxiv_score,
        web=web_score,
    )

    score_snapshot = ScoreSnapshot(
        subject_id=person.id,
        rubric_version="signal-v1",
        components=components,
        evidence_ids=[],
    )
    session.add(score_snapshot)
    await session.flush()

    logger.info(
        "signal_score_computed",
        person_id=str(person.id),
        composite=components.get("composite"),
    )
    return components


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


async def discover_job(ctx: dict[str, Any], query: str, source: str) -> dict[str, Any]:
    """Run a connector's discover phase.

    Args:
        ctx: Arq context (contains redis, session_factory, etc.).
        query: Search query (e.g. "AI infra Berlin").
        source: Connector source_type (e.g. "github", "tavily_search").

    Returns:
        Summary dict with person_count, above_threshold_count.
    """
    logger.info("discover_job_started", query=query, source=source)
    connector = get_connector(source)
    seeds = await connector.discover(query)
    logger.info("discover_job_seeds", source=source, seed_count=len(seeds))

    above_count = 0
    async with _session_ctx(ctx) as session:
        for seed in seeds:
            person = await _get_or_create_person(
                session,
                source_type=source,
                handle=seed.handle,
                display_hint=seed.display_hint,
            )

            # Light collect: get metadata
            try:
                collected = await connector.collect(seed, depth="light")
            except Exception as exc:
                logger.error(
                    "collect_light_failed",
                    source=source, handle=seed.handle, error=str(exc),
                )
                continue

            snapshot = await _write_snapshot(session, collected)
            await _write_observations(session, snapshot, collected.observations, person.id)

            # Compute signal score
            components = await _compute_and_store_signal(session, person, source)

            # Enqueue deep collect if above threshold
            from app.config import get_settings as _get_settings
            settings = ctx.get("settings") or _get_settings()
            threshold = settings.signal_threshold

            if above_threshold(components, threshold):
                above_count += 1
                task = {
                    "person_id": str(person.id),
                    "source": source,
                    "depth": "deep",
                    "handle": seed.handle,
                }
                p = compute_priority(
                    info_gain=info_gain(components.get("composite", 0.0), staleness_days=0.0),
                    cost=connector.cost,
                    authority=connector.authority,
                )
                await queue_enqueue(ctx["redis"], task, p)

        await session.commit()

    logger.info("discover_job_completed", query=query, source=source, above=above_count)
    return {"query": query, "source": source, "seeds": len(seeds), "above_threshold": above_count}


async def collect_job(
    ctx: dict[str, Any],
    person_id: str,
    source: str,
    depth: str = "deep",
    handle: str = "",
) -> dict[str, Any]:
    """Run a connector's collect phase for a specific person.

    Args:
        ctx: Arq context.
        person_id: UUID of the Person to collect for.
        source: Connector source_type.
        depth: "light" or "deep".
        handle: The handle/identifier within the source.

    Returns:
        Summary dict.
    """
    logger.info("collect_job_started", person_id=person_id, source=source, depth=depth)

    async with _session_ctx(ctx) as session:
        # Resolve person
        result = await session.execute(select(Person).where(Person.id == person_id))
        person = result.scalar_one_or_none()
        if person is None:
            logger.error("collect_job_person_not_found", person_id=person_id)
            return {"error": "person_not_found"}

        # Resolve handle from person.handles if not provided
        if not handle and person.handles:
            handle = person.handles.get(source, "")

        connector = get_connector(source)
        seed = Seed(
            source_type=source,
            handle=handle,
            display_hint=person.display_name or handle,
        )

        try:
            collected = await connector.collect(seed, depth=depth)  # type: ignore[arg-type]
        except Exception as exc:
            logger.error(
                "collect_deep_failed",
                person_id=person_id, source=source, error=str(exc),
            )
            return {"error": str(exc)}

        snapshot = await _write_snapshot(session, collected)
        await _write_observations(session, snapshot, collected.observations, person.id)

        # Recompute signal score after deep collect
        await _compute_and_store_signal(session, person, source)

        await session.commit()

    obs_count = len(collected.observations)
    logger.info("collect_job_completed", person_id=person_id, source=source, depth=depth)
    return {"person_id": person_id, "source": source, "depth": depth, "observations": obs_count}


async def dispatcher_job(ctx: dict[str, Any]) -> dict[str, Any]:
    """Periodic cron: pop from Redis priority queue and enqueue Arq jobs.

    Respects concurrency limits and Tavily budget.
    """
    from app.config import get_settings

    settings = ctx.get("settings") or get_settings()
    redis = ctx["redis"]
    concurrency = settings.collection_concurrency

    # Check Tavily budget
    tavily_remaining = await get_tavily_budget_remaining(redis)
    if tavily_remaining <= 0:
        logger.warning("tavily_budget_exhausted")
        # Still process non-Tavily tasks

    tasks = await pop_top(redis, concurrency)
    enqueued = 0
    for task in tasks:
        source = task.get("source", "")
        if source == "tavily_search" and tavily_remaining <= 0:
            # Re-enqueue with lower priority for later
            await queue_enqueue(redis, task, priority=0.1)
            continue

        if source == "tavily_search":
            await decrement_tavily_budget(redis)
            tavily_remaining -= 1

        # Enqueue as Arq job
        await enqueue_arq_job(ctx, task)
        enqueued += 1

    depths = await queue_depth(redis)
    logger.info("dispatcher_job_completed", enqueued=enqueued, queue_depths=depths)
    return {"enqueued": enqueued, "queue_depths": depths}


async def enqueue_arq_job(ctx: dict[str, Any], task: dict[str, Any]) -> None:
    """Enqueue an Arq job from a task dict.

    Uses ctx['redis'] which is the ArqRedis pool (set by the Worker).
    """
    pool = ctx["redis"]
    job_type = task.get("job_type", "collect")
    if job_type == "discover":
        await pool.enqueue_job(
            "discover_job",
            task.get("query", ""),
            task.get("source", ""),
        )
    else:
        await pool.enqueue_job(
            "collect_job",
            task.get("person_id", ""),
            task.get("source", ""),
            task.get("depth", "deep"),
            task.get("handle", ""),
        )


async def recompute_signals_job(ctx: dict[str, Any]) -> dict[str, Any]:
    """Periodic cron: re-evaluate signal scores for all persons with new observations.

    Enqueues deep-collect for newly-crossing persons (with staleness guard).
    """
    from app.config import get_settings

    settings = ctx.get("settings") or get_settings()

    async with _session_ctx(ctx) as session:
        # Find persons with observations but no recent signal score
        result = await session.execute(
            select(Person).order_by(Person.updated_at.desc()).limit(500)
        )
        persons = result.scalars().all()

        above_count = 0
        for person in persons:
            components = await _compute_and_store_signal(session, person, "recompute")

            if above_threshold(components, settings.signal_threshold):
                above_count += 1
                # Check if already enqueued for deep collect (staleness guard)
                # For MVP, we re-enqueue; staleness check is Phase 2.
                for source_type in ("github", "producthunt", "arxiv", "web"):
                    task = {
                        "person_id": str(person.id),
                        "source": source_type,
                        "depth": "deep",
                    }
                    p = compute_priority(
                        info_gain=info_gain(
                            components.get("composite", 0.0), staleness_days=30.0,
                        ),
                        cost=1.0,
                        authority=0.7,
                    )
                    await queue_enqueue(ctx["redis"], task, p)

        await session.commit()

    logger.info("recompute_signals_completed", persons=len(persons), above=above_count)
    return {"persons_checked": len(persons), "above_threshold": above_count}
