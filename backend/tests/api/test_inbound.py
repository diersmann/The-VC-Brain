"""Tests for inbound pitch queueing helpers."""

from unittest.mock import AsyncMock

import pytest

from app.api.routes.inbound import _enqueue_inbound_pitch


@pytest.mark.asyncio
async def test_enqueue_inbound_pitch_closes_redis_pool() -> None:
    redis = AsyncMock()

    await _enqueue_inbound_pitch(
        redis,
        person_id="person-1",
        snapshot_id="snapshot-1",
        opportunity_id="opportunity-1",
        company_name="Acme",
    )

    redis.enqueue_job.assert_awaited_once_with(
        "process_inbound_pitch_job",
        person_id="person-1",
        snapshot_id="snapshot-1",
        opportunity_id="opportunity-1",
        company_name="Acme",
        _queue_name="arq:queue",
    )
    redis.aclose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_enqueue_inbound_pitch_closes_redis_pool_on_enqueue_failure() -> None:
    redis = AsyncMock()
    redis.enqueue_job.side_effect = RuntimeError("redis unavailable")

    with pytest.raises(RuntimeError, match="redis unavailable"):
        await _enqueue_inbound_pitch(
            redis,
            person_id="person-1",
            snapshot_id="snapshot-1",
            opportunity_id="opportunity-1",
            company_name="Acme",
        )

    redis.aclose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_enqueue_inbound_pitch_forwards_optional_job_id_and_evidence() -> None:
    redis = AsyncMock()

    await _enqueue_inbound_pitch(
        redis,
        person_id="person-1",
        snapshot_id="snapshot-1",
        opportunity_id="opportunity-1",
        company_name="Acme",
        founder_evidence={"learning_velocity": "Built a prototype"},
        job_id="job-1",
    )

    redis.enqueue_job.assert_awaited_once_with(
        "process_inbound_pitch_job",
        person_id="person-1",
        snapshot_id="snapshot-1",
        opportunity_id="opportunity-1",
        company_name="Acme",
        founder_evidence={"learning_velocity": "Built a prototype"},
        job_id="job-1",
        _queue_name="arq:queue",
    )
