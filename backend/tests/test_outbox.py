"""Durable outbox dispatch tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.db.models import OutboxEvent
from app.outbox import dispatch_pending_outbox


def _event() -> OutboxEvent:
    now = datetime.now(UTC)
    return OutboxEvent(
        id=uuid.uuid4(),
        dedupe_key="inbound-submission:key-1",
        event_type="inbound_pitch.accepted",
        aggregate_id=uuid.uuid4(),
        payload={"job_name": "process_inbound_pitch_job", "kwargs": {"snapshot_id": "snap-1"}},
        status="pending",
        attempts=0,
        available_at=now,
        created_at=now,
        updated_at=now,
    )


def _session(event: OutboxEvent) -> AsyncMock:
    session = AsyncMock()
    result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [event]))
    session.execute.return_value = result
    return session


@pytest.mark.asyncio
async def test_dispatch_marks_event_after_redis_accepts_job() -> None:
    event = _event()
    session = _session(event)
    redis = AsyncMock()

    result = await dispatch_pending_outbox(session, redis)

    assert result == {"found": 1, "dispatched": 1, "failed": 0}
    assert event.status == "dispatched"
    assert event.dispatched_at is not None
    redis.enqueue_job.assert_awaited_once_with(
        "process_inbound_pitch_job", snapshot_id="snap-1", _queue_name="arq:queue"
    )
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_keeps_event_pending_after_redis_failure() -> None:
    event = _event()
    session = _session(event)
    redis = AsyncMock()
    redis.enqueue_job.side_effect = ConnectionError("redis unavailable")

    result = await dispatch_pending_outbox(session, redis)

    assert result == {"found": 1, "dispatched": 0, "failed": 1}
    assert event.status == "pending"
    assert event.attempts == 1
    assert event.last_error == "redis unavailable"
    assert event.available_at > datetime.now(UTC)
    session.commit.assert_awaited_once()
