"""Credential-free discovery job contract and failure coverage."""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fakeredis import FakeAsyncRedis

from app.collectors import jobs
from app.collectors.base import ConnectorError
from app.collectors.queue import get_discovery_page, rollback_discovery_page
from app.db.models import JobRun


@pytest.mark.asyncio
async def test_discover_job_persists_rate_limit_as_retryable_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="discover", status="queued", phase="queued")
    session = AsyncMock()

    async def get(model: object, _job_id: object) -> JobRun | None:
        return job if model is JobRun else None

    session.get.side_effect = get

    @asynccontextmanager
    async def session_context(_ctx: dict[str, object]):
        yield session

    monkeypatch.setattr(jobs, "_session_ctx", session_context)
    monkeypatch.setattr(
        "app.collectors.queue.get_discovery_page", AsyncMock(return_value=1)
    )
    monkeypatch.setattr(
        "app.collectors.queue.rollback_discovery_page",
        AsyncMock(side_effect=RuntimeError("redis unavailable")),
    )
    connector = SimpleNamespace(
        discover=AsyncMock(side_effect=ConnectorError("github_rate_limited: HTTP 403"))
    )
    monkeypatch.setattr(jobs, "get_connector", lambda _source: connector)

    with pytest.raises(ConnectorError, match="rate_limited"):
        await jobs.discover_job(
            {"redis": object(), "session_factory": object()},
            "AI founders",
            "github",
            job_id=str(job.id),
        )

    assert job.status == "failed"
    assert job.result == {
        "status": "failed",
        "error": "github_rate_limited: HTTP 403",
        "failure_kind": "rate_limited",
        "retryable": True,
    }
    assert job.last_error == "github_rate_limited: HTTP 403"
    assert session.commit.await_count == 2


@pytest.mark.asyncio
async def test_discover_job_success_clears_previous_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(
        id=uuid.uuid4(),
        job_type="discover",
        status="queued",
        phase="queued",
        last_error="previous rate limit",
    )
    session = AsyncMock()
    session.get.return_value = job

    @asynccontextmanager
    async def session_context(_ctx: dict[str, object]):
        yield session

    monkeypatch.setattr(jobs, "_session_ctx", session_context)
    monkeypatch.setattr(
        "app.collectors.queue.get_discovery_page", AsyncMock(return_value=1)
    )
    connector = SimpleNamespace(discover=AsyncMock(return_value=[]))
    monkeypatch.setattr(jobs, "get_connector", lambda _source: connector)

    result = await jobs.discover_job(
        {
            "redis": object(),
            "session_factory": object(),
            "settings": SimpleNamespace(signal_threshold=0.8),
        },
        "AI founders",
        "github",
        job_id=str(job.id),
    )

    assert result["seeds"] == 0
    assert job.status == "succeeded"
    assert job.last_error is None


@pytest.mark.asyncio
async def test_discover_job_returns_terminal_result_for_non_retryable_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="discover", status="queued", phase="queued")
    session = AsyncMock()
    session.get.return_value = job

    @asynccontextmanager
    async def session_context(_ctx: dict[str, object]):
        yield session

    monkeypatch.setattr(jobs, "_session_ctx", session_context)
    monkeypatch.setattr("app.collectors.queue.get_discovery_page", AsyncMock(return_value=1))
    rollback = AsyncMock()
    monkeypatch.setattr("app.collectors.queue.rollback_discovery_page", rollback)
    connector = SimpleNamespace(
        discover=AsyncMock(side_effect=ConnectorError("github_search_failed: HTTP 404"))
    )
    monkeypatch.setattr(jobs, "get_connector", lambda _source: connector)

    result = await jobs.discover_job(
        {"redis": object(), "session_factory": object()},
        "AI founders",
        "github",
        job_id=str(job.id),
    )

    assert result == {
        "status": "failed",
        "error": "github_search_failed: HTTP 404",
        "failure_kind": "permanent",
        "retryable": False,
    }
    assert job.status == "failed"
    rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_discover_job_rolls_back_and_terminalizes_post_discover_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="discover", status="running", phase="collect")
    session = AsyncMock()
    session.get.return_value = job

    @asynccontextmanager
    async def session_context(_ctx: dict[str, object]):
        yield session

    async def failed_impl(
        ctx: dict[str, object],
        _query: str,
        _source: str,
        *,
        _reservation_key: str,
        job_id: str | None = None,
    ) -> dict[str, object]:
        reservations = ctx.setdefault("_discover_reservations", {})
        reservations[_reservation_key] = {"page": 1, "handled": False, "attempt": 2}
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(jobs, "_session_ctx", session_context)
    rollback = AsyncMock()
    monkeypatch.setattr("app.collectors.queue.rollback_discovery_page", rollback)
    monkeypatch.setattr(jobs, "_discover_job_impl", failed_impl)

    result = await jobs.discover_job(
        {"redis": object(), "session_factory": object()},
        "AI founders",
        "github",
        job_id=str(job.id),
    )

    assert result["status"] == "failed"
    assert result["retryable"] is False
    assert result["failure_kind"] == "permanent"
    assert job.status == "failed"
    rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_discovery_page_is_retried_without_skipping() -> None:
    redis = FakeAsyncRedis(decode_responses=True)

    page = await get_discovery_page(redis, "github", "AI founders")
    assert page == 1

    await rollback_discovery_page(redis, "github", "AI founders", page)

    assert await get_discovery_page(redis, "github", "AI founders") == 1
    await redis.aclose()


@pytest.mark.asyncio
async def test_stale_page_rollback_does_not_move_a_newer_reservation_backwards() -> None:
    redis = FakeAsyncRedis(decode_responses=True)

    first = await get_discovery_page(redis, "github", "AI founders")
    second = await get_discovery_page(redis, "github", "AI founders")
    assert (first, second) == (1, 2)

    await rollback_discovery_page(redis, "github", "AI founders", first)
    assert await redis.get("vcbrain:page:github:AI founders") == "2"

    await rollback_discovery_page(redis, "github", "AI founders", second)
    assert await redis.get("vcbrain:page:github:AI founders") == "1"
    await redis.aclose()


@pytest.mark.asyncio
async def test_page_wraparound_reservation_is_unique_under_concurrency() -> None:
    redis = FakeAsyncRedis(decode_responses=True)
    await redis.set("vcbrain:page:github:AI founders", 10)

    pages = await asyncio.gather(
        get_discovery_page(redis, "github", "AI founders"),
        get_discovery_page(redis, "github", "AI founders"),
    )

    assert set(pages) == {1, 2}
    await redis.aclose()
