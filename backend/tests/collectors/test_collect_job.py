"""Focused durable ledger coverage for collection workers."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.collectors import jobs
from app.collectors.base import Collected
from app.db.models import JobRun


def _session_for(person: object | None, job: JobRun) -> AsyncMock:
    if job.status is None:
        job.status = "queued"
    if job.phase is None:
        job.phase = "queued"
    if job.attempt is None:
        job.attempt = 0
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: person)

    async def get(model: object, _job_id: object) -> JobRun | None:
        return job if model is JobRun else None

    session.get.side_effect = get
    return session


def _patch_session(monkeypatch: pytest.MonkeyPatch, session: AsyncMock) -> None:
    @asynccontextmanager
    async def context(_ctx: dict[str, object]):
        yield session

    monkeypatch.setattr(jobs, "_session_ctx", context)


def _collected() -> Collected:
    return Collected(
        content=b"snapshot",
        content_type="text/plain",
        observations=[],
        source_type="github",
        uri="https://github.example/profile",
    )


def _person(person_id: uuid.UUID) -> SimpleNamespace:
    return SimpleNamespace(
        id=person_id,
        handles={"github": "founder"},
        display_name="Founder",
    )


@pytest.mark.asyncio
async def test_collect_job_marks_successful_run(monkeypatch: pytest.MonkeyPatch) -> None:
    person_id = uuid.uuid4()
    job = JobRun(id=uuid.uuid4(), job_type="collect", attempt=0)
    session = _session_for(_person(person_id), job)
    _patch_session(monkeypatch, session)
    connector = SimpleNamespace(collect=AsyncMock(return_value=_collected()))
    monkeypatch.setattr(jobs, "get_connector", lambda _source: connector)
    monkeypatch.setattr(jobs, "_write_snapshot", AsyncMock(return_value=SimpleNamespace(id=1)))
    monkeypatch.setattr(jobs, "_write_observations", AsyncMock())
    monkeypatch.setattr(jobs, "_compute_and_store_signal", AsyncMock())

    result = await jobs.collect_job(
        {"session_factory": object()}, str(person_id), "github", job_id=str(job.id)
    )

    assert result == {
        "person_id": str(person_id),
        "source": "github",
        "depth": "deep",
        "observations": 0,
    }
    assert job.status == "succeeded"
    assert job.attempt == 1
    assert job.result == result


@pytest.mark.asyncio
async def test_collect_job_creates_worker_run_when_id_is_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    person_id = uuid.uuid4()
    job = JobRun(id=uuid.uuid4(), job_type="collect", attempt=0)
    session = _session_for(_person(person_id), job)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(jobs, "create_job", AsyncMock(return_value=job))
    connector = SimpleNamespace(collect=AsyncMock(return_value=_collected()))
    monkeypatch.setattr(jobs, "get_connector", lambda _source: connector)
    monkeypatch.setattr(jobs, "_write_snapshot", AsyncMock(return_value=SimpleNamespace(id=1)))
    monkeypatch.setattr(jobs, "_write_observations", AsyncMock())
    monkeypatch.setattr(jobs, "_compute_and_store_signal", AsyncMock())

    result = await jobs.collect_job({"session_factory": object()}, str(person_id), "github")

    assert result["person_id"] == str(person_id)
    assert job.status == "succeeded"
    jobs.create_job.assert_awaited_once_with(session, "collect")


@pytest.mark.asyncio
async def test_collect_job_skips_duplicate_terminal_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    person_id = uuid.uuid4()
    job = JobRun(
        id=uuid.uuid4(),
        job_type="collect",
        status="succeeded",
        attempt=3,
        result={"person_id": str(person_id), "status": "succeeded"},
    )
    session = _session_for(_person(person_id), job)
    _patch_session(monkeypatch, session)
    connector = SimpleNamespace(collect=AsyncMock())
    monkeypatch.setattr(jobs, "get_connector", lambda _source: connector)

    result = await jobs.collect_job(
        {"session_factory": object()}, str(person_id), "github", job_id=str(job.id)
    )

    assert result == job.result
    connector.collect.assert_not_awaited()
    assert job.attempt == 3


@pytest.mark.asyncio
async def test_collect_job_persists_classified_connector_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    person_id = uuid.uuid4()
    job = JobRun(id=uuid.uuid4(), job_type="collect", attempt=0)
    session = _session_for(_person(person_id), job)
    _patch_session(monkeypatch, session)
    connector = SimpleNamespace(collect=AsyncMock(side_effect=RuntimeError("HTTP 429 rate limit")))
    monkeypatch.setattr(jobs, "get_connector", lambda _source: connector)

    result = await jobs.collect_job(
        {"session_factory": object()}, str(person_id), "github", job_id=str(job.id)
    )

    assert result["status"] == "failed"
    assert result["failure_kind"] == "rate_limited"
    assert result["retryable"] is True
    assert job.status == "failed"
    assert job.result == result
    assert job.last_error == "HTTP 429 rate limit"


@pytest.mark.asyncio
async def test_collect_job_terminalizes_missing_person(monkeypatch: pytest.MonkeyPatch) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="collect", attempt=0)
    session = _session_for(None, job)
    _patch_session(monkeypatch, session)

    result = await jobs.collect_job(
        {"session_factory": object()}, str(uuid.uuid4()), "github", job_id=str(job.id)
    )

    assert result == {
        "status": "failed",
        "error": "person_not_found",
        "failure_kind": "permanent",
        "retryable": False,
    }
    assert job.status == "failed"
    assert job.result == {
        "status": "failed",
        "error": "person_not_found",
        "failure_kind": "permanent",
        "retryable": False,
    }


@pytest.mark.asyncio
async def test_collect_job_finalizes_unexpected_failure_and_reraises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    person_id = uuid.uuid4()
    job = JobRun(id=uuid.uuid4(), job_type="collect", attempt=0)
    session = _session_for(_person(person_id), job)
    _patch_session(monkeypatch, session)
    connector = SimpleNamespace(collect=AsyncMock(return_value=_collected()))
    monkeypatch.setattr(jobs, "get_connector", lambda _source: connector)
    monkeypatch.setattr(jobs, "_write_snapshot", AsyncMock(side_effect=RuntimeError("db exploded")))

    with pytest.raises(RuntimeError, match="db exploded"):
        await jobs.collect_job(
            {"session_factory": object()}, str(person_id), "github", job_id=str(job.id)
        )

    assert job.status == "failed"
    assert job.result is not None
    assert job.result["failure_kind"] == "permanent"
    session.rollback.assert_awaited_once()
