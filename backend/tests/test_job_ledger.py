"""Tests for durable job lifecycle helpers."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.db.models import JobRun
from app.job_ledger import update_job


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
