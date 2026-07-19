"""Shared helpers for opportunity lifecycle management.

Used by discover_job, advance_pipeline_job, contact_job, and the
research/scoring/memo jobs to find-or-create opportunities and record
lifecycle transitions with auditable DecisionEvents.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DecisionEvent, Opportunity, OpportunityFounder, Person

logger = structlog.get_logger(__name__)


async def get_or_create_opportunity(
    session: AsyncSession,
    person: Person,
    *,
    source_kind: str = "outbound",
    lifecycle_state: str = "discovered",
    company_name: str | None = None,
) -> Opportunity:
    """Find the latest opportunity for *person*, or create one.

    If an opportunity already exists, return it as-is (do not change its
    lifecycle state — the caller decides whether to transition).
    """
    result = await session.execute(
        select(Opportunity)
        .join(OpportunityFounder, OpportunityFounder.opportunity_id == Opportunity.id)
        .where(OpportunityFounder.person_id == person.id)
        .order_by(Opportunity.created_at.desc())
        .limit(1)
    )
    opportunity = result.scalar_one_or_none()
    if opportunity is not None:
        return opportunity

    opportunity = Opportunity(
        company_name=company_name or person.display_name or person.stable_id,
        source_kind=source_kind,
        lifecycle_state=lifecycle_state,
    )
    session.add(opportunity)
    await session.flush()
    session.add(OpportunityFounder(opportunity_id=opportunity.id, person_id=person.id))
    await session.flush()
    return opportunity


async def create_inbound_opportunity(
    session: AsyncSession,
    person: Person,
    *,
    company_name: str | None = None,
    thesis_version: str | None = None,
) -> Opportunity:
    """Create a new inbound opportunity for a person (e.g. after mock reply)."""
    opportunity = Opportunity(
        company_name=company_name or person.display_name or person.stable_id,
        source_kind="inbound",
        lifecycle_state="received",
        thesis_version=thesis_version,
    )
    session.add(opportunity)
    await session.flush()
    session.add(OpportunityFounder(opportunity_id=opportunity.id, person_id=person.id))
    await session.flush()
    return opportunity


async def has_inbound_opportunity(session: AsyncSession, person_id: uuid.UUID) -> bool:
    """Check if a person already has an inbound opportunity."""
    result = await session.execute(
        select(Opportunity.id)
        .join(OpportunityFounder, OpportunityFounder.opportunity_id == Opportunity.id)
        .where(
            OpportunityFounder.person_id == person_id,
            Opportunity.source_kind == "inbound",
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def transition_opportunity(
    session: AsyncSession,
    opportunity: Opportunity,
    new_state: str,
    *,
    actor: str = "pipeline:auto",
    reason: str = "",
) -> DecisionEvent:
    """Transition an opportunity to *new_state* and write a DecisionEvent.

    Raises ValueError if the transition is invalid.
    """
    from app.lifecycle import advance_reason, is_valid_transition

    prior_state = opportunity.lifecycle_state
    if not is_valid_transition(prior_state, new_state):
        msg = f"Invalid lifecycle transition: {prior_state} -> {new_state}"
        raise ValueError(msg)

    if prior_state == new_state:
        # Idempotent: no transition needed, but return a no-op event marker
        return DecisionEvent(
            opportunity_id=opportunity.id,
            prior_state=prior_state,
            new_state=new_state,
            actor=actor,
            reason=f"(no-op) {reason or advance_reason(prior_state, new_state)}",
            sla_metadata={},
        )

    opportunity.lifecycle_state = new_state
    event = DecisionEvent(
        opportunity_id=opportunity.id,
        prior_state=prior_state,
        new_state=new_state,
        actor=actor,
        reason=reason or advance_reason(prior_state, new_state),
        sla_metadata={},
    )
    session.add(event)
    await session.flush()

    logger.info(
        "lifecycle_transition",
        opportunity_id=str(opportunity.id),
        prior=prior_state,
        new=new_state,
        actor=actor,
        reason=reason,
    )
    return event