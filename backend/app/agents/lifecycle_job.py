"""Pipeline advancement job — auto-transitions opportunities through lifecycle stages.

Runs every 2 minutes via cron.  Each transition is idempotent and checks
for output existence before advancing.  Handles stuck-state recovery and
LLM budget gating.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.jobs import _session_ctx
from app.collectors.queue import (
    decrement_agent_budget,
    get_agent_budget_remaining,
)
from app.collectors.queue import (
    enqueue as queue_enqueue,
)
from app.db.models import (
    DecisionEvent,
    InvestmentMemo,
    Observation,
    Opportunity,
    OpportunityFounder,
    Person,
    ScoreSnapshot,
)
from app.opportunity_service import transition_opportunity

logger = structlog.get_logger(__name__)

# Maximum retries before closing a stuck opportunity
_MAX_RETRIES = 3
_INVESTIGATION_AGENT_CALLS = 5  # 3 specialists + critic + batched embeddings


async def _count_retries(session: AsyncSession, opportunity_id: Any) -> int:
    """Count how many times a pipeline job has retried for this opportunity."""
    result = await session.execute(
        select(DecisionEvent)
        .where(
            DecisionEvent.opportunity_id == opportunity_id,
            DecisionEvent.actor == "pipeline:auto",
            DecisionEvent.reason.like("%retry%"),
        )
        .order_by(DecisionEvent.created_at.desc())
    )
    return len(result.scalars().all())


async def _has_recent_pipeline_event(
    session: AsyncSession,
    opportunity_id: Any,
    reason_fragment: str,
    since: datetime,
) -> bool:
    """Return whether a matching pipeline event was written recently."""
    result = await session.execute(
        select(DecisionEvent.id)
        .where(
            DecisionEvent.opportunity_id == opportunity_id,
            DecisionEvent.actor == "pipeline:auto",
            DecisionEvent.reason.like(f"%{reason_fragment}%"),
            DecisionEvent.created_at >= since,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _has_score(session: AsyncSession, person_id: Any) -> bool:
    """Check if a person has a founder-agent-v1 score."""
    result = await session.execute(
        select(ScoreSnapshot.id)
        .where(
            ScoreSnapshot.subject_id == person_id,
            ScoreSnapshot.rubric_version == "founder-agent-v1",
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _has_memo(session: AsyncSession, opportunity_id: Any) -> bool:
    """Check if an opportunity has an investment memo."""
    result = await session.execute(
        select(InvestmentMemo.id)
        .where(
            InvestmentMemo.opportunity_id == opportunity_id,
            InvestmentMemo.status == "succeeded",
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _has_observations(session: AsyncSession, person_id: Any) -> bool:
    """Check if a person has any observations."""
    result = await session.execute(
        select(Observation.id)
        .where(Observation.subject_id == person_id)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def advance_pipeline_job(ctx: dict[str, Any]) -> dict[str, Any]:
    """Auto-advance all opportunities through the lifecycle pipeline.

    Runs every 2 minutes.  Idempotent — each transition checks for output
    existence before advancing.
    """
    from app.config import get_settings

    settings = ctx.get("settings") or get_settings()
    redis = ctx["redis"]
    logger.info("advance_pipeline_job_started")

    transitions = 0
    stuck_closed = 0
    budget_exhausted = 0

    async with _session_ctx(ctx) as session:
        # Fetch all non-terminal opportunities
        result = await session.execute(
            select(Opportunity)
            .where(
                Opportunity.lifecycle_state.notin_(["approved", "closed"]),
            )
            .order_by(Opportunity.created_at.asc())
            .limit(settings.pipeline_batch_size)
        )
        opportunities: list[Opportunity] = list(result.scalars().all())

        for opp in opportunities:
            state = opp.lifecycle_state

            # Resolve the person for this opportunity
            founder_result = await session.execute(
                select(Person)
                .join(OpportunityFounder, OpportunityFounder.person_id == Person.id)
                .where(OpportunityFounder.opportunity_id == opp.id)
                .limit(1)
            )
            person = founder_result.scalar_one_or_none()
            if person is None:
                continue

            # --- discovered -> interesting ---
            if state == "discovered":
                # Check the latest signal score
                score_result = await session.execute(
                    select(ScoreSnapshot)
                    .where(
                        ScoreSnapshot.subject_id == person.id,
                        ScoreSnapshot.rubric_version == "signal-v1",
                    )
                    .order_by(ScoreSnapshot.created_at.desc())
                    .limit(1)
                )
                score = score_result.scalar_one_or_none()
                if score is not None:
                    composite = float(str(score.components.get("composite", 0.0)))
                    if composite >= settings.signal_threshold:
                        reason = (
                            f"Signal composite {composite:.3f} >= "
                            f"threshold {settings.signal_threshold}"
                        )
                        await transition_opportunity(
                            session, opp, "interesting", reason=reason,
                        )
                        transitions += 1

            # --- interesting -> investigating ---
            elif state == "interesting":
                if await _has_score(session, person.id):
                    # Already scored — skip
                    continue
                budget = await get_agent_budget_remaining(redis)
                if budget < _INVESTIGATION_AGENT_CALLS:
                    budget_exhausted += 1
                    continue
                await decrement_agent_budget(redis, _INVESTIGATION_AGENT_CALLS)
                await transition_opportunity(
                    session, opp, "investigating",
                    reason="Investigation started — research, scoring, and processing queued",
                )
                transitions += 1
                # Enqueue the three investigation jobs
                await queue_enqueue(
                    redis,
                    {"job_type": "research_candidate", "person_id": str(person.id)},
                    priority=10.0,
                )
                await queue_enqueue(
                    redis,
                    {"job_type": "score_candidate", "person_id": str(person.id)},
                    priority=10.0,
                )
                await queue_enqueue(
                    redis,
                    {"job_type": "process_candidate", "person_id": str(person.id)},
                    priority=10.0,
                )

            # --- investigating -> outreach draft (if above contact threshold) ---
            elif state == "investigating":
                if not await _has_score(session, person.id):
                    # Still being scored — retry only after the configured
                    # stuck interval, preventing duplicate in-flight jobs.
                    cutoff = datetime.now(UTC) - timedelta(
                        minutes=settings.pipeline_stuck_after_minutes
                    )
                    if opp.updated_at and opp.updated_at > cutoff:
                        continue
                    retries = await _count_retries(session, opp.id)
                    if retries >= _MAX_RETRIES:
                        await transition_opportunity(
                            session, opp, "closed",
                            reason=f"Pipeline timeout after {_MAX_RETRIES} retries",
                        )
                        stuck_closed += 1
                    else:
                        budget = await get_agent_budget_remaining(redis)
                        if budget < _INVESTIGATION_AGENT_CALLS:
                            budget_exhausted += 1
                            continue
                        await decrement_agent_budget(redis, _INVESTIGATION_AGENT_CALLS)
                        for job_type in (
                            "research_candidate",
                            "score_candidate",
                            "process_candidate",
                        ):
                            await queue_enqueue(
                                redis,
                                {"job_type": job_type, "person_id": str(person.id)},
                                priority=10.0,
                            )
                        session.add(
                            DecisionEvent(
                                opportunity_id=opp.id,
                                prior_state="investigating",
                                new_state="investigating",
                                actor="pipeline:auto",
                                reason=f"Pipeline retry {retries + 1}",
                                sla_metadata={"retry": retries + 1},
                            )
                        )
                        opp.updated_at = datetime.now(UTC)
                    continue

                # Check the agent score composite
                score_result = await session.execute(
                    select(ScoreSnapshot)
                    .where(
                        ScoreSnapshot.subject_id == person.id,
                        ScoreSnapshot.rubric_version == "founder-agent-v1",
                    )
                    .order_by(ScoreSnapshot.created_at.desc())
                    .limit(1)
                )
                score = score_result.scalar_one_or_none()
                if score is None:
                    continue
                composite = float(str(score.components.get("founder", 0.0))) * 100  # 0-1 -> 0-100
                if composite >= settings.contact_threshold * 100:
                    budget = await get_agent_budget_remaining(redis)
                    if budget <= 0:
                        budget_exhausted += 1
                        continue
                    await decrement_agent_budget(redis, 1)
                    reason = (
                        f"Agent composite {composite:.1f} >= "
                        f"contact threshold {settings.contact_threshold * 100:.0f}"
                    )
                    session.add(
                        DecisionEvent(
                            opportunity_id=opp.id,
                            prior_state="investigating",
                            new_state="investigating",
                            actor="pipeline:auto",
                            reason=f"Outreach draft requested — {reason}",
                            sla_metadata={"outreach_status": "drafted"},
                        )
                    )
                    opp.updated_at = datetime.now(UTC)
                    await queue_enqueue(
                        redis,
                        {"job_type": "contact_outbound", "person_id": str(person.id)},
                        priority=10.0,
                    )

            # --- contacted: waits for the founder to submit via /submit ---
            elif state == "contacted":
                # The founder's actual submission via /submit creates a new
                # inbound opportunity at "received". Keep this outbound
                # opportunity at "contacted" for conversion tracking and
                # audit history.
                continue

            # --- received -> memo_ready ---
            elif state == "received":
                if await _has_memo(session, opp.id):
                    await transition_opportunity(
                        session, opp, "memo_ready",
                        reason="Investment memo generated",
                    )
                    transitions += 1
                else:
                    # Enqueue memo generation if it has not been queued
                    # recently. This avoids one enqueue every cron cycle.
                    budget = await get_agent_budget_remaining(redis)
                    cutoff = datetime.now(UTC) - timedelta(
                        minutes=settings.pipeline_stuck_after_minutes
                    )
                    recently_queued = await _has_recent_pipeline_event(
                        session, opp.id, "Memo generation queued", cutoff
                    )
                    if budget > 0 and not recently_queued:
                        await decrement_agent_budget(redis, 1)
                        await queue_enqueue(
                            redis,
                            {"job_type": "generate_memo", "person_id": str(person.id)},
                            priority=10.0,
                        )
                        session.add(
                            DecisionEvent(
                                opportunity_id=opp.id,
                                prior_state="received",
                                new_state="received",
                                actor="pipeline:auto",
                                reason="Memo generation queued",
                                sla_metadata={},
                            )
                        )

            # --- memo_ready -> (human decision via existing endpoint) ---
            # No auto-transition — human decides via POST /{id}/decision

        await session.commit()

    logger.info(
        "advance_pipeline_job_completed",
        opportunities=len(opportunities),
        transitions=transitions,
        stuck_closed=stuck_closed,
        budget_exhausted=budget_exhausted,
    )
    return {
        "opportunities": len(opportunities),
        "transitions": transitions,
        "stuck_closed": stuck_closed,
        "budget_exhausted": budget_exhausted,
    }
