"""Mock cold outreach and inbound reply jobs.

``contact_outbound_job`` generates an outreach email (via the existing
agent) and transitions the opportunity to "contacted".  It then schedules
a ``mock_inbound_reply_job`` after a configurable delay.

``mock_inbound_reply_job`` creates a new inbound opportunity with mock
deck observations, simulating a founder reply.  It is idempotent — if
an inbound opportunity already exists for this person, it skips.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from app.agents.outreach import draft_outreach_email
from app.collectors.jobs import _session_ctx
from app.db.models import Observation, Opportunity, OpportunityFounder, Person, SourceSnapshot
from app.opportunity_service import (
    create_inbound_opportunity,
    has_inbound_opportunity,
    transition_opportunity,
)
from app.storage import put_snapshot

logger = structlog.get_logger(__name__)


async def contact_outbound_job(ctx: dict[str, Any], person_id: str) -> dict[str, Any]:
    """Generate a mock outreach email and transition to 'contacted'.

    Schedules a mock_inbound_reply_job after mock_reply_delay_seconds.
    """
    from app.config import get_settings

    settings = ctx.get("settings") or get_settings()
    logger.info("contact_outbound_job_started", person_id=person_id)

    async with _session_ctx(ctx) as session:
        person = await session.get(Person, uuid.UUID(person_id))
        if person is None:
            logger.error("contact_person_not_found", person_id=person_id)
            return {"error": "person_not_found"}

        # Find the outbound opportunity
        opp_result = await session.execute(
            select(Opportunity)
            .join(OpportunityFounder, OpportunityFounder.opportunity_id == Opportunity.id)
            .where(
                OpportunityFounder.person_id == person.id,
                Opportunity.source_kind == "outbound",
            )
            .order_by(Opportunity.created_at.desc())
            .limit(1)
        )
        opportunity = opp_result.scalar_one_or_none()
        if opportunity is None:
            logger.error("contact_no_opportunity", person_id=person_id)
            return {"error": "no_opportunity"}

        # Generate outreach email (uses existing agent with template fallback)
        gh_handle = person.handles.get("github", "N/A") if person.handles else "N/A"
        draft = await draft_outreach_email(
            founder_name=person.display_name or person.stable_id,
            company=opportunity.company_name,
            email_type="founder_intro",
            brief="We discovered your work and would love to learn more.",
            evidence_summary=f"GitHub: {gh_handle}",
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )

        # Write the outreach email as an observation
        now = datetime.now(UTC)
        outreach_content = f"Subject: {draft.subject}\n\n{draft.body}".encode()
        content_hash, storage_path = await put_snapshot(
            outreach_content, "text/plain", "outreach"
        )
        snapshot = SourceSnapshot(
            uri=f"outreach://{person.stable_id}",
            source_type="outreach",
            content_hash=content_hash,
            storage_path=storage_path,
            collected_at=now,
        )
        session.add(snapshot)
        await session.flush()

        session.add(
            Observation(
                snapshot_id=snapshot.id,
                subject_id=person.id,
                predicate="outreach_email_draft",
                object_value=f"Subject: {draft.subject}\n\n{draft.body}",
                observed_at=now,
                extractor_version="outreach-v1",
                confidence=0.9,
            )
        )

        # Transition to contacted
        await transition_opportunity(
            session, opportunity, "contacted",
            reason=f"Cold outreach sent (mock) — mode={draft.generation_mode}",
        )

        # Schedule mock reply
        delay = settings.mock_reply_delay_seconds
        await ctx["redis"].enqueue_job(
            "mock_inbound_reply_job",
            person_id,
            _defer_by=delay,
        )

        await session.commit()

    logger.info(
        "contact_outbound_job_completed",
        person_id=person_id,
        mode=draft.generation_mode,
        reply_delay=delay,
    )
    return {
        "person_id": person_id,
        "mode": draft.generation_mode,
        "reply_delay": delay,
    }


async def mock_inbound_reply_job(ctx: dict[str, Any], person_id: str) -> dict[str, Any]:
    """Simulate a founder reply to the outreach.

    Creates a new inbound opportunity with mock deck observations.
    Idempotent — skips if an inbound opportunity already exists.
    """
    logger.info("mock_inbound_reply_job_started", person_id=person_id)

    async with _session_ctx(ctx) as session:
        person = await session.get(Person, uuid.UUID(person_id))
        if person is None:
            logger.error("mock_reply_person_not_found", person_id=person_id)
            return {"error": "person_not_found"}

        # Idempotency check: skip if inbound already exists
        if await has_inbound_opportunity(session, person.id):
            logger.info("mock_reply_skipped_inbound_exists", person_id=person_id)
            return {"skipped": "inbound_opportunity_already_exists"}

        # Create inbound opportunity
        company = person.display_name or person.stable_id
        opportunity = await create_inbound_opportunity(
            session, person, company_name=company, thesis_version="mock-v1",
        )

        # Write mock deck observations
        now = datetime.now(UTC)
        mock_content = f"Mock deck for {company}".encode()
        content_hash, storage_path = await put_snapshot(
            mock_content, "text/plain", "mock_inbound"
        )
        snapshot = SourceSnapshot(
            uri=f"mock://{person.stable_id}/deck",
            source_type="mock_inbound",
            content_hash=content_hash,
            storage_path=storage_path,
            collected_at=now,
        )
        session.add(snapshot)
        await session.flush()

        mock_observations = [
            ("inbound_summary", "Interested in discussing our company — here is our deck."),
            ("pitch_deck_url", f"https://example.com/decks/{person.stable_id}.pdf"),
            ("pitch_deck_stage", "Seed"),
            ("pitch_deck_title", f"{company} — Company Overview"),
            ("company", company),
        ]
        for predicate, value in mock_observations:
            session.add(
                Observation(
                    snapshot_id=snapshot.id,
                    subject_id=person.id,
                    predicate=predicate,
                    object_value=value,
                    observed_at=now,
                    extractor_version="mock-v1",
                    confidence=0.5,
                )
            )

        await session.commit()

    logger.info("mock_inbound_reply_job_completed", person_id=person_id, company=company)
    return {
        "person_id": person_id,
        "company": company,
        "inbound_opportunity_id": str(opportunity.id),
    }
