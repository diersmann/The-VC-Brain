"""Cold outreach job.

``contact_outbound_job`` generates a human-reviewable outreach draft. It
never claims that a provider sent the email; approval and delivery are
separate lifecycle actions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from app.agents.outreach import draft_outreach_email
from app.collectors.jobs import _session_ctx
from app.db.models import (
    Observation,
    Opportunity,
    OpportunityFounder,
    OutreachMessage,
    Person,
    SourceSnapshot,
)
from app.outreach_delivery import contact_block_reason
from app.privacy import external_ai_use_decision, redact_direct_identifiers
from app.source_policy import build_source_use_policy
from app.storage import put_snapshot

logger = structlog.get_logger(__name__)


async def contact_outbound_job(ctx: dict[str, Any], person_id: str) -> dict[str, Any]:
    """Generate a persisted outreach draft without claiming provider delivery.

    The email invites the founder to submit their pitch deck at the
    /submit endpoint.  No mock reply is scheduled — the founder's
    actual submission via /submit creates the inbound opportunity.
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

        existing_result = await session.execute(
            select(OutreachMessage)
            .where(
                OutreachMessage.person_id == person.id,
                OutreachMessage.opportunity_id == opportunity.id,
                OutreachMessage.status != "failed",
            )
            .order_by(OutreachMessage.created_at.desc())
            .limit(1)
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            return {
                "person_id": person_id,
                "status": existing.status,
                "outreach_id": str(existing.id),
            }

        block_reason = contact_block_reason(person)
        if block_reason:
            blocked_status = "opted_out" if block_reason.startswith("suppressed_") else "failed"
            message = OutreachMessage(
                opportunity_id=opportunity.id,
                person_id=person.id,
                recipient_email=person.email,
                status=blocked_status,
                failure_reason=block_reason,
            )
            session.add(message)
            await session.commit()
            return {
                "person_id": person_id,
                "status": blocked_status,
                "error": block_reason,
            }

        # Generate outreach email (uses existing agent with template fallback)
        gh_handle = person.handles.get("github", "N/A") if person.handles else "N/A"
        ai_policy = external_ai_use_decision(person, "outreach")
        draft = await draft_outreach_email(
            founder_name=person.display_name or person.stable_id,
            company=opportunity.company_name,
            email_type="founder_intro",
            brief="We discovered your work and would love to learn more.",
            evidence_summary=redact_direct_identifiers(f"Public activity signal: {gh_handle}"),
            api_key=settings.llm_api_key if ai_policy.allowed else "",
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
            source_use_policy=build_source_use_policy("outreach", {"model_use": "allowed"}),
            collected_at=now,
        )
        session.add(snapshot)
        await session.flush()

        session.add(
            Observation(
                snapshot_id=snapshot.id,
                subject_id=person.id,
                opportunity_id=opportunity.id,
                predicate="outreach_email_draft",
                object_value=f"Subject: {draft.subject}\n\n{draft.body}",
                observed_at=now,
                extractor_version="outreach-v1",
                confidence=0.9,
            )
        )

        message = OutreachMessage(
            opportunity_id=opportunity.id,
            person_id=person.id,
            recipient_email=person.email,
            subject=draft.subject,
            body=draft.body,
            generation_mode=draft.generation_mode,
            status="drafted",
        )
        session.add(message)

        await session.commit()

    logger.info(
        "contact_outbound_job_completed",
        person_id=person_id,
        mode=draft.generation_mode,
    )
    return {
        "person_id": person_id,
        "mode": draft.generation_mode,
        "status": "drafted",
        "outreach_id": str(message.id),
    }
