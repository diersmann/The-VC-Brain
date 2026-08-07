"""Durable queue-entry coverage for periodic thesis discovery."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.collectors import jobs
from app.db.models import JobRun


def _session(active_thesis: object | None) -> AsyncMock:
    result = SimpleNamespace(scalar_one_or_none=lambda: active_thesis)
    session = AsyncMock()
    session.execute.return_value = result
    return session


def _thesis(*queries: str) -> SimpleNamespace:
    return SimpleNamespace(discovery_queries=list(queries))


def _job() -> JobRun:
    return JobRun(id=uuid.uuid4(), job_type="discover", status="queued", phase="queued")


def _patch_session(monkeypatch: pytest.MonkeyPatch, session: AsyncMock) -> None:
    @asynccontextmanager
    async def context(_ctx: dict[str, object]):
        yield session

    monkeypatch.setattr(jobs, "_session_ctx", context)


@pytest.mark.asyncio
async def test_auto_discovery_without_active_thesis_is_a_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session(None)
    _patch_session(monkeypatch, session)
    create = AsyncMock()
    enqueue = AsyncMock()
    monkeypatch.setattr(jobs, "create_job", create)
    monkeypatch.setattr(jobs, "queue_enqueue", enqueue)

    result = await jobs.auto_discovery_job({"redis": object()})

    assert result == {"enqueued": 0, "failed": 0}
    create.assert_not_awaited()
    enqueue.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_discovery_creates_one_job_per_query_and_forwards_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session(_thesis("AI founders", "climate founders"))
    _patch_session(monkeypatch, session)
    created = [_job(), _job()]
    create = AsyncMock(side_effect=created)
    enqueue = AsyncMock()
    monkeypatch.setattr(jobs, "create_job", create)
    monkeypatch.setattr(jobs, "queue_enqueue", enqueue)

    result = await jobs.auto_discovery_job({"redis": object()})

    assert result == {"enqueued": 2, "failed": 0}
    assert [call.args[:2] for call in create.await_args_list] == [
        (session, "discover"),
        (session, "discover"),
    ]
    assert all("job_id" in call.kwargs for call in create.await_args_list)
    assert [call.args[1] for call in enqueue.await_args_list] == [
        {
            "job_type": "discover",
            "query": "AI founders",
            "source": "github",
            "job_id": str(created[0].id),
        },
        {
            "job_type": "discover",
            "query": "climate founders",
            "source": "github",
            "job_id": str(created[1].id),
        },
    ]
    assert [call.kwargs for call in enqueue.await_args_list] == [
        {"priority": 5.0},
        {"priority": 5.0},
    ]
    # Each deterministic row is durable before Redis fan-out, and the final
    # commit persists any queue-entry outcomes.
    assert session.commit.await_count == 2


@pytest.mark.asyncio
async def test_auto_discovery_deduplicates_repeated_thesis_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session(_thesis("AI founders", "AI founders"))
    _patch_session(monkeypatch, session)
    created = _job()
    session.get.side_effect = [None, created]
    create = AsyncMock(return_value=created)
    enqueue = AsyncMock()
    monkeypatch.setattr(jobs, "create_job", create)
    monkeypatch.setattr(jobs, "queue_enqueue", enqueue)

    result = await jobs.auto_discovery_job({"redis": object()})

    assert result == {"enqueued": 1, "failed": 0}
    create.assert_awaited_once()
    enqueue.assert_awaited_once()
    assert session.commit.await_count == 1


@pytest.mark.asyncio
async def test_auto_discovery_retries_same_bucket_queue_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session(_thesis("AI founders"))
    _patch_session(monkeypatch, session)
    existing = _job()
    existing.status = "failed"
    existing.phase = "queue"
    existing.last_error = "queue_failed"
    existing.result = {"status": "failed", "error": "queue_failed"}
    session.get.return_value = existing
    create = AsyncMock()
    enqueue = AsyncMock()
    monkeypatch.setattr(jobs, "create_job", create)
    monkeypatch.setattr(jobs, "queue_enqueue", enqueue)

    result = await jobs.auto_discovery_job({"redis": object()})

    assert result == {"enqueued": 1, "failed": 0}
    create.assert_not_awaited()
    enqueue.assert_awaited_once()
    assert existing.status == "queued"
    assert existing.last_error is None
    assert existing.result is None
    assert session.commit.await_count == 1


@pytest.mark.asyncio
async def test_auto_discovery_marks_only_failed_queue_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session(_thesis("AI founders", "climate founders"))
    _patch_session(monkeypatch, session)
    created = [_job(), _job()]
    session.get.side_effect = [None, None, created[1]]
    create = AsyncMock(side_effect=created)
    enqueue = AsyncMock(side_effect=[None, RuntimeError("redis unavailable")])
    monkeypatch.setattr(jobs, "create_job", create)
    monkeypatch.setattr(jobs, "queue_enqueue", enqueue)

    result = await jobs.auto_discovery_job({"redis": object()})

    assert result == {"enqueued": 1, "failed": 1}
    assert created[1].status == "failed"
    assert created[1].phase == "queue"
    assert created[1].last_error == "queue_failed"
    assert created[1].result == {
        "status": "failed",
        "error": "queue_failed",
        "error_type": "RuntimeError",
    }
    assert session.commit.await_count == 3
