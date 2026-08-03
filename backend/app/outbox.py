"""Durable outbox creation and retryable Redis dispatch."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import InboundSubmission, OutboxEvent


def inbound_outbox_event(submission: InboundSubmission, company_name: str) -> OutboxEvent:
    """Build the one dispatch event associated with an inbound submission."""
    return OutboxEvent(
        dedupe_key=f"inbound-submission:{submission.idempotency_key}",
        event_type="inbound_pitch.accepted",
        aggregate_id=submission.opportunity_id,
        payload={
            "job_name": "process_inbound_pitch_job",
            "kwargs": {
                "person_id": str(submission.person_id),
                "snapshot_id": str(submission.snapshot_id),
                "opportunity_id": str(submission.opportunity_id),
                "company_name": company_name,
                "founder_evidence": submission.founder_evidence,
            },
        },
    )


async def dispatch_pending_outbox(
    session: AsyncSession,
    redis: Any,
    *,
    limit: int = 50,
) -> dict[str, int]:
    """Dispatch ready events, leaving failures pending for a later retry."""
    now = datetime.now(UTC)
    result = await session.execute(
        select(OutboxEvent)
        .where(OutboxEvent.status == "pending", OutboxEvent.available_at <= now)
        .order_by(OutboxEvent.created_at)
        .limit(max(1, min(limit, 200)))
        .with_for_update(skip_locked=True)
    )
    events = list(result.scalars().all())
    dispatched = 0
    failed = 0

    for event in events:
        payload = event.payload
        try:
            job_name = str(payload["job_name"])
            kwargs = payload.get("kwargs", {})
            if not isinstance(kwargs, dict):
                raise ValueError("outbox kwargs must be an object")
            await redis.enqueue_job(job_name, **kwargs, _queue_name="arq:queue")
        except Exception as exc:
            event.attempts += 1
            event.available_at = now + timedelta(seconds=min(300, 2 ** min(event.attempts, 8)))
            event.last_error = str(exc)[:1000]
            failed += 1
        else:
            event.status = "dispatched"
            event.dispatched_at = now
            event.last_error = None
            dispatched += 1

    await session.commit()
    return {"found": len(events), "dispatched": dispatched, "failed": failed}
