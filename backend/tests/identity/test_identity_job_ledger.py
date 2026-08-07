"""Durable JobRun coverage for identity-resolution workers."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from app.collectors import jobs
from app.db.models import JobRun


def _session_for(job: JobRun) -> AsyncMock:
    if job.status is None:
        job.status = "queued"
    if job.phase is None:
        job.phase = "queued"
    if job.attempt is None:
        job.attempt = 0
    session = AsyncMock()

    async def get(model: object, _identifier: object) -> JobRun | None:
        return job if model is JobRun else None

    session.get.side_effect = get
    return session


def _patch_session(monkeypatch: pytest.MonkeyPatch, session: AsyncMock) -> None:
    @asynccontextmanager
    async def context(_ctx: dict[str, object]):
        yield session

    monkeypatch.setattr(jobs, "_session_ctx", context)


@pytest.mark.asyncio
async def test_identity_worker_creates_and_completes_job(monkeypatch: pytest.MonkeyPatch) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="resolve_identities", attempt=0)
    session = _session_for(job)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(jobs, "create_job", AsyncMock(return_value=job))
    monkeypatch.setattr(
        "app.identity.resolve_identities",
        AsyncMock(return_value={"pairs_checked": 2, "merged": 1, "flagged": 1}),
    )

    result = await jobs.resolve_identities_job({"session_factory": object(), "redis": object()})

    assert result == {"pairs_checked": 2, "merged": 1, "flagged": 1}
    assert job.status == "succeeded"
    assert job.result == result


@pytest.mark.asyncio
async def test_identity_failure_is_classified_and_finalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="resolve_identities", attempt=0)
    session = _session_for(job)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(
        "app.identity.resolve_identities",
        AsyncMock(side_effect=TimeoutError("identity provider timed out")),
    )

    with pytest.raises(TimeoutError, match="identity provider timed out"):
        await jobs.resolve_identities_job(
            {"session_factory": object(), "redis": object()}, str(job.id)
        )

    assert job.status == "failed"
    assert job.result is not None
    assert job.result["failure_kind"] == "transient"
    assert job.result["retryable"] is True
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_identity_terminal_duplicate_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    job = JobRun(
        id=uuid.uuid4(),
        job_type="resolve_identities",
        status="succeeded",
        phase="complete",
        attempt=2,
        result={"pairs_checked": 3, "merged": 0, "flagged": 0},
    )
    session = _session_for(job)
    _patch_session(monkeypatch, session)
    resolver = AsyncMock()
    monkeypatch.setattr("app.identity.resolve_identities", resolver)

    result = await jobs.resolve_identities_job(
        {"session_factory": object(), "redis": object()}, str(job.id)
    )

    assert result == job.result
    resolver.assert_not_awaited()


@pytest.mark.asyncio
async def test_identity_failed_job_retries_with_incremented_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(
        id=uuid.uuid4(),
        job_type="resolve_identities",
        status="failed",
        phase="identity",
        attempt=2,
    )
    session = _session_for(job)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(
        "app.identity.resolve_identities",
        AsyncMock(return_value={"pairs_checked": 1, "merged": 0, "flagged": 1}),
    )

    await jobs.resolve_identities_job(
        {"session_factory": object(), "redis": object()}, str(job.id)
    )

    assert job.status == "succeeded"
    assert job.attempt == 3
