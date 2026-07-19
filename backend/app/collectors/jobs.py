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

import asyncio
import json
import re
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.avatars import fetch_and_store_avatar
from app.collectors.base import Collected, Seed
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
from app.db.models import (
    Assessment,
    Claim,
    Observation,
    Opportunity,
    OpportunityFounder,
    Person,
    ScoreSnapshot,
    SourceSnapshot,
)
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
    """Find a Person by handle in the JSONB handles column, or create one.

    If the found person has been merged (``canonical = False``), follows
    the supersession chain to return the canonical Person.
    """
    # Try to find existing person with this handle
    result = await session.execute(
        select(Person).where(Person.handles[source_type].as_string() == handle)
    )
    person = result.scalar_one_or_none()
    if person is not None:
        # Follow supersession chain to canonical
        while not person.canonical and person.superseded_by_id:
            person = await session.get(Person, person.superseded_by_id)
            if person is None:
                break
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
) -> list[uuid.UUID]:
    """Write Observation rows linked to a SourceSnapshot."""
    now = datetime.now(UTC)
    observation_ids: list[uuid.UUID] = []
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
        observation_ids.append(observation.id)
    return observation_ids


async def _compute_and_store_signal(
    session: AsyncSession,
    person: Person,
    source_type: str,
) -> dict[str, float]:
    """Compute a signal score from existing observations and store as ScoreSnapshot."""
    # Fetch all observations for this person
    result = await session.execute(select(Observation).where(Observation.subject_id == person.id))
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
            github_score = compute_github_signal(total_stars=int(val) if val.isdigit() else 0)
        elif pred == "producthunt_total_upvotes":
            producthunt_score = compute_producthunt_signal(
                total_upvotes=int(val) if val.isdigit() else 0
            )
        elif pred == "arxiv_total_citations":
            arxiv_score = compute_arxiv_signal(total_citations=int(val) if val.isdigit() else 0)
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

    # Auto-advance page to find new people each run
    from app.collectors.queue import get_discovery_page

    page = await get_discovery_page(ctx["redis"], source, query)
    logger.info("discover_job_page", source=source, query=query, page=page)

    seeds = await connector.discover(query, page=page)
    logger.info("discover_job_seeds", source=source, seed_count=len(seeds))

    above_count = 0
    from app.config import get_settings as _get_settings

    settings = ctx.get("settings") or _get_settings()
    threshold = settings.signal_threshold

    async with _session_ctx(ctx) as session:
        for seed in seeds:
            person = await _get_or_create_person(
                session,
                source_type=source,
                handle=seed.handle,
                display_hint=seed.display_hint,
            )

            # Staleness check: skip light collect if this person was already
            # collected from this source recently (within freshness window).
            from app.collectors.thesis_config import get_thesis_config

            thesis = get_thesis_config()
            freshness_days = thesis.get("source_freshness_days", {}).get(source, 7)
            from datetime import UTC, datetime, timedelta

            cutoff = datetime.now(UTC) - timedelta(days=freshness_days)

            recent_snapshot = await session.execute(
                select(SourceSnapshot)
                .join(Observation, Observation.snapshot_id == SourceSnapshot.id)
                .where(
                    Observation.subject_id == person.id,
                    SourceSnapshot.source_type == source,
                    SourceSnapshot.collected_at >= cutoff,
                )
                .limit(1)
            )
            if recent_snapshot.scalar_one_or_none() is not None:
                logger.debug(
                    "discover_skip_fresh",
                    person_id=str(person.id),
                    source=source,
                )
                # Still recompute signal score with existing observations
                components = await _compute_and_store_signal(session, person, source)
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
                continue

            # Light collect: get metadata
            try:
                collected = await connector.collect(seed, depth="light")
            except Exception as exc:
                logger.error(
                    "collect_light_failed",
                    source=source,
                    handle=seed.handle,
                    error=str(exc),
                )
                continue

            snapshot = await _write_snapshot(session, collected)
            await _write_observations(session, snapshot, collected.observations, person.id)

            # Update Person display_name from observations if available
            for obs in collected.observations:
                if obs.get("predicate") == "display_name":
                    name_val = str(obs.get("object_value", "")).strip()
                    if name_val and name_val != person.display_name:
                        person.display_name = name_val
                    break

            # Compute signal score
            components = await _compute_and_store_signal(session, person, source)

            # Enqueue deep collect if above threshold
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
                person_id=person_id,
                source=source,
                error=str(exc),
            )
            return {"error": str(exc)}

        snapshot = await _write_snapshot(session, collected)
        await _write_observations(session, snapshot, collected.observations, person.id)

        # Collection can start from a handle-only seed. Promote a verified
        # public display name from the source profile so Discover does not
        # keep showing or hiding the raw handle after enrichment.
        for observation in collected.observations:
            if observation.get("predicate") != "display_name":
                continue
            display_name = str(observation.get("object_value", "")).strip()
            if display_name and display_name.lower() != handle.lower():
                person.display_name = display_name
            break

        # Recompute signal score after deep collect
        await _compute_and_store_signal(session, person, source)

        await session.commit()

    obs_count = len(collected.observations)
    logger.info("collect_job_completed", person_id=person_id, source=source, depth=depth)
    return {"person_id": person_id, "source": source, "depth": depth, "observations": obs_count}


async def fetch_candidate_avatar_job(ctx: dict[str, Any], person_id: str) -> dict[str, Any]:
    """Cache one candidate avatar, preferring verified public LinkedIn imagery."""
    settings = ctx["settings"]
    async with _session_ctx(ctx) as session:
        person = await session.get(Person, uuid.UUID(person_id))
        if person is None or not person.canonical:
            return {"person_id": person_id, "status": "not_found"}

        avatar = await fetch_and_store_avatar(
            session,
            person,
            github_token=settings.github_token,
        )
        if avatar is None:
            return {"person_id": person_id, "status": "unavailable"}
        await session.commit()

    logger.info(
        "candidate_avatar_completed",
        person_id=person_id,
        source=avatar.source_type,
        bytes=len(avatar.data),
    )
    return {
        "person_id": person_id,
        "status": "completed",
        "source": avatar.source_type,
        "bytes": len(avatar.data),
    }


# ---------------------------------------------------------------------------
# Tavily candidate research + multi-axis scoring
# ---------------------------------------------------------------------------

_AXIS_LABELS = {
    "founder": "Founder",
    "market": "Market",
    "idea_market": "Idea-Market",
}

_AXIS_KEYWORDS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "founder": (
        (
            "founder",
            "co-founder",
            "built",
            "launched",
            "led",
            "scaled",
            "acquired",
            "patent",
            "open source",
            "award",
        ),
        ("fraud", "lawsuit", "misconduct", "controversy", "bankrupt", "sanction"),
    ),
    "market": (
        (
            "market growth",
            "cagr",
            "demand",
            "adoption",
            "billion",
            "funding",
            "tailwind",
            "expanding",
        ),
        (
            "shrinking",
            "saturated",
            "commoditized",
            "regulatory risk",
            "declining demand",
            "crowded",
        ),
    ),
    "idea_market": (
        (
            "customer",
            "revenue",
            "pilot",
            "traction",
            "contract",
            "users",
            "launch",
            "product-market fit",
            "growth",
        ),
        ("no revenue", "pre-revenue", "shutdown", "pivoted away", "no customers", "stalled"),
    ),
}


def _candidate_company(observations: list[Observation], person: Person) -> str:
    for predicate in ("company", "company_name", "github_company", "organization"):
        for observation in observations:
            if observation.predicate.lower() == predicate and observation.object_value.strip():
                return observation.object_value.strip().lstrip("@")[0:512]
    return person.display_name or person.stable_id


def _research_queries(person: Person, company: str) -> dict[str, str]:
    name = person.display_name or person.stable_id
    handles = " ".join((person.handles or {}).values())
    subject = f'"{name}" {handles}'.strip()
    company_term = f'"{company}"' if company and company != name else subject
    return {
        "founder": (
            f"{subject} founder track record leadership previous companies "
            "achievements execution reputation"
        ),
        "market": f"{company_term} product sector market size growth competitors industry outlook",
        "idea_market": (
            f"{company_term} product customers revenue traction pilots contracts adoption reviews"
        ),
    }


def score_research_axis(
    axis: str,
    response: dict[str, Any],
    subject_terms: list[str],
) -> dict[str, float]:
    """Turn Tavily relevance and evidence language into an explainable 0..1 score."""
    results_raw = response.get("results", [])
    results = results_raw if isinstance(results_raw, list) else []
    answer = str(response.get("answer", "") or "")
    texts = [answer]
    relevances: list[float] = []
    domains: set[str] = set()
    for item in results:
        if not isinstance(item, dict):
            continue
        texts.append(f"{item.get('title', '')} {item.get('content', '')}")
        raw_score = item.get("score", 0.0)
        if isinstance(raw_score, (int, float)):
            relevances.append(max(0.0, min(1.0, float(raw_score))))
        url = str(item.get("url", ""))
        match = re.match(r"https?://([^/]+)", url)
        if match:
            domains.add(match.group(1).lower().removeprefix("www."))

    corpus = " ".join(texts).lower()
    positive_words, negative_words = _AXIS_KEYWORDS[axis]
    positive_hits = sum(corpus.count(word) for word in positive_words)
    negative_hits = sum(corpus.count(word) for word in negative_words)
    relevance = sum(relevances) / len(relevances) if relevances else 0.0
    diversity = min(1.0, len(domains) / 5.0)
    coverage = min(1.0, len(results) / 5.0)
    term_hits = sum(1 for term in subject_terms if term and term.lower() in corpus)
    identity_match = min(1.0, term_hits / max(1, min(2, len(subject_terms))))
    positive_signal = min(1.0, positive_hits / 6.0)
    negative_signal = min(1.0, negative_hits / 3.0)

    if not results:
        score = 0.30
        confidence = 0.0
    else:
        score = (
            0.18
            + 0.27 * relevance
            + 0.14 * diversity
            + 0.18 * positive_signal
            + 0.13 * identity_match
            + 0.10 * coverage
            - 0.18 * negative_signal
        )
        confidence = (
            0.10 + 0.40 * relevance + 0.25 * coverage + 0.15 * diversity + 0.10 * identity_match
        )

    return {
        "score": round(max(0.05, min(0.95, score)), 4),
        "confidence": round(max(0.0, min(0.95, confidence)), 4),
        "relevance": round(relevance, 4),
        "source_diversity": round(diversity, 4),
        "positive_signal": round(positive_signal, 4),
        "negative_signal": round(negative_signal, 4),
        "result_count": float(len(results)),
    }


def _rating(score: float) -> str:
    if score >= 0.67:
        return "Bullish"
    if score < 0.42:
        return "Bearish"
    return "Neutral"


def _trend(score: float, previous: float | None) -> str:
    if previous is None or abs(score - previous) < 0.05:
        return "Stable"
    return "Improving" if score > previous else "Declining"


def _axis_unknowns(axis: str, result_count: int, confidence: float) -> list[str]:
    unknowns: list[str] = []
    if result_count < 3:
        unknowns.append("Fewer than three relevant public sources were found")
    if confidence < 0.55:
        unknowns.append("Evidence confidence is below the investment-review threshold")
    if axis == "founder":
        unknowns.append("Private references and team feedback require human diligence")
    elif axis == "market":
        unknowns.append("Bottom-up market sizing has not been independently verified")
    else:
        unknowns.append("Customer retention and unit economics require primary evidence")
    return unknowns


async def research_candidate_job(ctx: dict[str, Any], person_id: str) -> dict[str, Any]:
    """Research one candidate with three Tavily searches and persist scored evidence."""
    from tavily import TavilyClient  # type: ignore[import-untyped]

    settings = ctx["settings"]
    if not settings.tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY is not configured")

    async with _session_ctx(ctx) as session:
        person = await session.get(Person, uuid.UUID(person_id))
        if person is None or not person.canonical:
            return {"error": "person_not_found", "person_id": person_id}

        existing_observations_result = await session.execute(
            select(Observation).where(Observation.subject_id == person.id)
        )
        existing_observations = list(existing_observations_result.scalars().all())
        company = _candidate_company(existing_observations, person)
        queries = _research_queries(person, company)

        previous_result = await session.execute(
            select(ScoreSnapshot)
            .where(
                ScoreSnapshot.subject_id == person.id,
                ScoreSnapshot.rubric_version == "founder-tavily-v1",
            )
            .order_by(ScoreSnapshot.created_at.desc())
            .limit(1)
        )
        previous_snapshot = previous_result.scalar_one_or_none()
        previous_components = previous_snapshot.components if previous_snapshot else {}

        client = TavilyClient(api_key=settings.tavily_api_key)
        axis_scores: dict[str, dict[str, float]] = {}
        axis_evidence: dict[str, list[str]] = {}
        axis_answers: dict[str, str] = {}

        for axis, query in queries.items():
            logger.info("candidate_research_axis_started", person_id=person_id, axis=axis)
            response = await asyncio.to_thread(
                client.search,
                query=query,
                search_depth="advanced",
                max_results=5,
                include_answer="advanced",
                include_raw_content=False,
            )
            subject_terms = [person.display_name or "", company, *(person.handles or {}).values()]
            scored = score_research_axis(axis, response, subject_terms)
            axis_scores[axis] = scored
            answer = str(response.get("answer", "") or "").strip()
            axis_answers[axis] = answer
            evidence_ids: list[str] = []

            results_raw = response.get("results", [])
            results = results_raw if isinstance(results_raw, list) else []
            for result in results:
                if not isinstance(result, dict):
                    continue
                url = str(result.get("url", ""))
                if not url:
                    continue
                content = json.dumps(result, ensure_ascii=False).encode("utf-8")
                relevance = result.get("score", 0.5)
                confidence = float(relevance) if isinstance(relevance, (int, float)) else 0.5
                collected = Collected(
                    content=content,
                    content_type="application/json",
                    observations=[
                        {
                            "predicate": f"research_{axis}_evidence",
                            "object_value": (
                                f"{result.get('title', '')} — {result.get('content', '')}"
                            ),
                            "observed_at": datetime.now(UTC),
                            "confidence": max(0.1, min(1.0, confidence)),
                        }
                    ],
                    source_type="tavily_search",
                    uri=url,
                    license_hint={"source": "Tavily Search", "query": query},
                )
                snapshot = await _write_snapshot(session, collected)
                ids = await _write_observations(
                    session, snapshot, collected.observations, person.id
                )
                evidence_ids.extend(str(item) for item in ids)

            if answer:
                summary_content = json.dumps(
                    {"query": query, "answer": answer}, ensure_ascii=False
                ).encode("utf-8")
                summary_collected = Collected(
                    content=summary_content,
                    content_type="application/json",
                    observations=[
                        {
                            "predicate": f"research_{axis}_summary",
                            "object_value": answer,
                            "observed_at": datetime.now(UTC),
                            "confidence": scored["confidence"],
                        }
                    ],
                    source_type="tavily_search",
                    uri="https://api.tavily.com/search",
                    license_hint={"source": "Tavily Search", "query": query},
                )
                summary_snapshot = await _write_snapshot(session, summary_collected)
                summary_ids = await _write_observations(
                    session, summary_snapshot, summary_collected.observations, person.id
                )
                evidence_ids.extend(str(item) for item in summary_ids)
                session.add(
                    Claim(
                        observation_ids=evidence_ids,
                        subject_id=person.id,
                        predicate=f"research_{axis}_summary",
                        object_value=answer,
                        status="tavily_synthesized",
                        confidence=scored["confidence"],
                        valid_time_start=datetime.now(UTC),
                    )
                )

            axis_evidence[axis] = evidence_ids

        opportunity_result = await session.execute(
            select(Opportunity)
            .join(OpportunityFounder, OpportunityFounder.opportunity_id == Opportunity.id)
            .where(OpportunityFounder.person_id == person.id)
            .order_by(Opportunity.created_at.desc())
            .limit(1)
        )
        opportunity = opportunity_result.scalar_one_or_none()
        if opportunity is None:
            opportunity = Opportunity(
                company_name=company,
                source_kind="outbound",
                lifecycle_state="screening",
                thesis_version="tavily-v1",
            )
            session.add(opportunity)
            await session.flush()
            session.add(OpportunityFounder(opportunity_id=opportunity.id, person_id=person.id))

        for axis, scored in axis_scores.items():
            previous_value = previous_components.get(axis)
            previous = float(previous_value) if isinstance(previous_value, (int, float)) else None
            session.add(
                Assessment(
                    opportunity_id=opportunity.id,
                    axis=_AXIS_LABELS[axis],
                    rating=_rating(scored["score"]),
                    trend=_trend(scored["score"], previous),
                    confidence=scored["confidence"],
                    evidence_ids=axis_evidence[axis],
                    counter_evidence_ids=[],
                    unknowns=_axis_unknowns(
                        axis, int(scored["result_count"]), scored["confidence"]
                    ),
                )
            )

        evidence_confidence = sum(item["confidence"] for item in axis_scores.values()) / 3
        score_components: dict[str, object] = {
            "founder": axis_scores["founder"]["score"],
            "market": axis_scores["market"]["score"],
            "idea_market": axis_scores["idea_market"]["score"],
            "evidence_confidence": round(evidence_confidence, 4),
            "founder_relevance": axis_scores["founder"]["relevance"],
            "market_relevance": axis_scores["market"]["relevance"],
            "idea_market_relevance": axis_scores["idea_market"]["relevance"],
        }
        session.add(
            ScoreSnapshot(
                subject_id=person.id,
                rubric_version="founder-tavily-v1",
                components=score_components,
                confidence_interval={
                    axis: {
                        "low": round(
                            max(0.0, scored["score"] - (1 - scored["confidence"]) * 0.2), 4
                        ),
                        "high": round(
                            min(1.0, scored["score"] + (1 - scored["confidence"]) * 0.2), 4
                        ),
                    }
                    for axis, scored in axis_scores.items()
                },
                evidence_ids=[item for ids in axis_evidence.values() for item in ids],
            )
        )
        await session.commit()

    logger.info("candidate_research_completed", person_id=person_id, scores=score_components)
    return {"person_id": person_id, "scores": score_components, "answers": axis_answers}


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
    elif job_type == "resolve_identities":
        await pool.enqueue_job("resolve_identities_job")
    elif job_type == "research_candidate":
        await pool.enqueue_job(
            "research_candidate_job",
            task.get("person_id", ""),
        )
    elif job_type == "fetch_candidate_avatar":
        await pool.enqueue_job(
            "fetch_candidate_avatar_job",
            task.get("person_id", ""),
        )
    elif job_type == "score_candidate":
        await pool.enqueue_job(
            "score_candidate_job",
            task.get("person_id", ""),
        )
    elif job_type == "generate_memo":
        await pool.enqueue_job(
            "generate_memo_job",
            task.get("person_id", ""),
        )
    elif job_type == "process_candidate":
        await pool.enqueue_job(
            "process_candidate_job",
            task.get("person_id", ""),
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
        result = await session.execute(select(Person).order_by(Person.updated_at.desc()).limit(500))
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
                            components.get("composite", 0.0),
                            staleness_days=30.0,
                        ),
                        cost=1.0,
                        authority=0.7,
                    )
                    await queue_enqueue(ctx["redis"], task, p)

        await session.commit()

    logger.info("recompute_signals_completed", persons=len(persons), above=above_count)
    return {"persons_checked": len(persons), "above_threshold": above_count}


async def resolve_identities_job(ctx: dict[str, Any]) -> dict[str, int]:
    """Periodic cron: run identity resolution across all canonical persons.

    Detects duplicate Person records from different sources and either
    auto-merges (high confidence) or flags for human review (medium confidence).
    """
    logger.info("resolve_identities_job_started")

    async with _session_ctx(ctx) as session:
        from app.identity import resolve_identities

        summary = await resolve_identities(session, ctx["redis"])
        await session.commit()

    logger.info("resolve_identities_job_completed", **summary)
    return summary
