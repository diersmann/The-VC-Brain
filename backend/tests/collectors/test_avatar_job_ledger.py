"""Durable JobRun coverage for candidate avatar workers."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.collectors import jobs
from app.collectors.avatars import AvatarPayload
from app.db.models import JobRun, Person


def _session_for(person: object | None, job: JobRun) -> AsyncMock:
    if job.status is None:
        job.status = "queued"
    if job.phase is None:
        job.phase = "queued"
    if job.attempt is None:
        job.attempt = 0
    session = AsyncMock()

    async def get(model: object, _identifier: object) -> object | None:
        if model is JobRun:
            return job
        if model is Person:
            return person
        return None

    session.get.side_effect = get
    return session


def _patch_session(monkeypatch: pytest.MonkeyPatch, session: AsyncMock) -> None:
    @asynccontextmanager
    async def context(_ctx: dict[str, object]):
        yield session

    monkeypatch.setattr(jobs, "_session_ctx", context)


def _payload() -> AvatarPayload:
    return AvatarPayload(
        data=b"avatar",
        mime_type="image/png",
        sha256="hash",
        source_type="github",
        source_url="https://github.com/founder",
        image_url="https://githubusercontent.com/avatar.png",
    )


def _person(person_id: uuid.UUID, *, canonical: bool = True) -> SimpleNamespace:
    return SimpleNamespace(id=person_id, canonical=canonical)


@pytest.mark.asyncio
async def test_avatar_worker_creates_and_completes_job(monkeypatch: pytest.MonkeyPatch) -> None:
    person_id = uuid.uuid4()
    job = JobRun(id=uuid.uuid4(), job_type="fetch_candidate_avatar", attempt=0)
    session = _session_for(_person(person_id), job)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(jobs, "create_job", AsyncMock(return_value=job))
    monkeypatch.setattr(jobs, "fetch_and_store_avatar", AsyncMock(return_value=_payload()))

    result = await jobs.fetch_candidate_avatar_job(
        {"session_factory": object(), "settings": SimpleNamespace(github_token="")},
        str(person_id),
    )

    assert result == {
        "person_id": str(person_id),
        "status": "completed",
        "source": "github",
        "bytes": 6,
    }
    assert job.status == "succeeded"
    assert job.result == result


@pytest.mark.asyncio
async def test_avatar_unavailable_is_terminal_failed_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    person_id = uuid.uuid4()
    job = JobRun(id=uuid.uuid4(), job_type="fetch_candidate_avatar", attempt=0)
    session = _session_for(_person(person_id), job)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(jobs, "fetch_and_store_avatar", AsyncMock(return_value=None))

    result = await jobs.fetch_candidate_avatar_job(
        {"session_factory": object(), "settings": SimpleNamespace(github_token="")},
        str(person_id),
        str(job.id),
    )

    assert result == {"person_id": str(person_id), "status": "unavailable"}
    assert job.status == "failed"
    assert job.result is not None
    assert job.result["error"] == "avatar_unavailable"


@pytest.mark.asyncio
async def test_avatar_missing_person_is_terminal_failed_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="fetch_candidate_avatar", attempt=0)
    session = _session_for(None, job)
    _patch_session(monkeypatch, session)

    result = await jobs.fetch_candidate_avatar_job(
        {"session_factory": object(), "settings": SimpleNamespace(github_token="")},
        str(uuid.uuid4()),
        str(job.id),
    )

    assert result["status"] == "not_found"
    assert job.status == "failed"
    assert job.result is not None
    assert job.result["failure_kind"] == "permanent"


@pytest.mark.asyncio
async def test_avatar_provider_failure_is_finalized_and_reraised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    person_id = uuid.uuid4()
    job = JobRun(id=uuid.uuid4(), job_type="fetch_candidate_avatar", attempt=0)
    session = _session_for(_person(person_id), job)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(
        jobs,
        "fetch_and_store_avatar",
        AsyncMock(side_effect=RuntimeError("provider timeout")),
    )

    with pytest.raises(RuntimeError, match="provider timeout"):
        await jobs.fetch_candidate_avatar_job(
            {"session_factory": object(), "settings": SimpleNamespace(github_token="")},
            str(person_id),
            str(job.id),
        )

    assert job.status == "failed"
    assert job.result is not None
    assert job.result["failure_kind"] == "transient"
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_avatar_duplicate_terminal_delivery_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    person_id = uuid.uuid4()
    job = JobRun(
        id=uuid.uuid4(),
        job_type="fetch_candidate_avatar",
        status="succeeded",
        phase="complete",
        attempt=2,
        result={"person_id": str(person_id), "status": "completed"},
    )
    session = _session_for(_person(person_id), job)
    _patch_session(monkeypatch, session)
    fetch = AsyncMock()
    monkeypatch.setattr(jobs, "fetch_and_store_avatar", fetch)

    result = await jobs.fetch_candidate_avatar_job(
        {"session_factory": object(), "settings": SimpleNamespace(github_token="")},
        str(person_id),
        str(job.id),
    )

    assert result == job.result
    fetch.assert_not_awaited()


@pytest.mark.asyncio
async def test_avatar_failed_job_reopens_with_incremented_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    person_id = uuid.uuid4()
    job = JobRun(
        id=uuid.uuid4(),
        job_type="fetch_candidate_avatar",
        status="failed",
        phase="avatar",
        attempt=2,
        last_error="previous timeout",
    )
    session = _session_for(_person(person_id), job)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(jobs, "fetch_and_store_avatar", AsyncMock(return_value=_payload()))

    result = await jobs.fetch_candidate_avatar_job(
        {"session_factory": object(), "settings": SimpleNamespace(github_token="")},
        str(person_id),
        str(job.id),
    )

    assert result["status"] == "completed"
    assert job.status == "succeeded"
    assert job.attempt == 3
