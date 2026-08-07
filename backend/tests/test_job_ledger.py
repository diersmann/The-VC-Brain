"""Tests for durable job lifecycle helpers."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.db.models import JobRun
from app.job_ledger import start_job, update_job


@pytest.mark.asyncio
async def test_update_job_clamps_progress_and_sets_terminal_metadata() -> None:
    job = JobRun(id=uuid.uuid4(), job_type="discover")
    session = AsyncMock()
    session.get.return_value = job

    result = await update_job(
        session,
        job.id,
        status="succeeded",
        phase="complete",
        attempt=1,
        progress=2.0,
        result={"seeds": 3},
    )

    assert result is job
    assert job.status == "succeeded"
    assert job.phase == "complete"
    assert job.progress == 1.0
    assert job.finished_at is not None
    assert job.result == {"seeds": 3}


@pytest.mark.asyncio
async def test_update_job_ignores_malformed_ids() -> None:
    session = AsyncMock()

    assert (
        await update_job(
            session,
            "not-a-uuid",
            status="failed",
            phase="error",
            last_error="bad id",
        )
        is None
    )
    session.get.assert_not_called()


@pytest.mark.asyncio
async def test_update_job_clears_previous_error_on_success() -> None:
    job = JobRun(id=uuid.uuid4(), job_type="score_candidate", last_error="stale")
    session = AsyncMock()
    session.get.return_value = job

    await update_job(
        session,
        job.id,
        status="succeeded",
        phase="complete",
        clear_error=True,
    )

    assert job.last_error is None


@pytest.mark.asyncio
async def test_start_job_advances_retry_attempt_and_clears_error() -> None:
    job = JobRun(id=uuid.uuid4(), job_type="research_candidate", attempt=2, last_error="timeout")
    session = AsyncMock()
    session.get.return_value = job

    result = await start_job(session, job.id, phase="research")

    assert result is job
    assert job.status == "running"
    assert job.phase == "research"
    assert job.attempt == 3
    assert job.last_error is None


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["succeeded", "cancelled"])
async def test_start_job_is_terminal_idempotent(status: str) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="memo", status=status, attempt=4)
    session = AsyncMock()
    session.get.return_value = job

    result = await start_job(session, job.id, phase="memo")

    assert result is job
    assert job.status == status
    assert job.attempt == 4
