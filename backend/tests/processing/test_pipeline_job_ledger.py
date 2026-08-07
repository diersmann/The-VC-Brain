"""Durable JobRun coverage for the processing pipeline worker."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.db.models import JobRun, Person
from app.processing import pipeline_job


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

    monkeypatch.setattr(pipeline_job, "_session_ctx", context)


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        llm_api_key="",
        embedding_model="test-model",
        embedding_concurrency=1,
    )


def _patch_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline_job, "reconcile_observations", AsyncMock(return_value=2))
    monkeypatch.setattr(pipeline_job, "embed_observations", AsyncMock(return_value=3))
    monkeypatch.setattr(pipeline_job, "deduplicate_claims", AsyncMock(return_value=1))


@pytest.mark.asyncio
async def test_processing_worker_creates_and_completes_job(monkeypatch: pytest.MonkeyPatch) -> None:
    person_id = uuid.uuid4()
    job = JobRun(id=uuid.uuid4(), job_type="process_candidate", attempt=0)
    session = _session_for(SimpleNamespace(id=person_id), job)
    _patch_session(monkeypatch, session)
    _patch_pipeline(monkeypatch)
    monkeypatch.setattr(pipeline_job, "create_job", AsyncMock(return_value=job))

    result = await pipeline_job.process_candidate_job(
        {"session_factory": object(), "settings": _settings()}, str(person_id)
    )

    assert result == {
        "person_id": str(person_id),
        "claims_created": 2,
        "embeddings_generated": 3,
        "claims_deduped": 1,
    }
    assert job.status == "succeeded"
    assert job.result == result


@pytest.mark.asyncio
async def test_processing_missing_person_is_terminal_failed_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="process_candidate", attempt=0)
    session = _session_for(None, job)
    _patch_session(monkeypatch, session)

    result = await pipeline_job.process_candidate_job(
        {"session_factory": object(), "settings": _settings()}, str(uuid.uuid4()), str(job.id)
    )

    assert result["error"] == "person_not_found"
    assert job.status == "failed"
    assert job.result is not None
    assert job.result["failure_kind"] == "permanent"


@pytest.mark.asyncio
async def test_processing_unexpected_failure_rolls_back_and_finalizes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    person_id = uuid.uuid4()
    job = JobRun(id=uuid.uuid4(), job_type="process_candidate", attempt=0)
    session = _session_for(SimpleNamespace(id=person_id), job)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(
        pipeline_job,
        "reconcile_observations",
        AsyncMock(side_effect=RuntimeError("reconcile exploded")),
    )

    with pytest.raises(RuntimeError, match="reconcile exploded"):
        await pipeline_job.process_candidate_job(
            {"session_factory": object(), "settings": _settings()},
            str(person_id),
            str(job.id),
        )

    assert job.status == "failed"
    assert job.result is not None
    assert job.result["error"] == "reconcile exploded"
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_processing_transient_embedding_failure_is_classified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    person_id = uuid.uuid4()
    job = JobRun(id=uuid.uuid4(), job_type="process_candidate", attempt=0)
    session = _session_for(SimpleNamespace(id=person_id), job)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(pipeline_job, "reconcile_observations", AsyncMock(return_value=1))
    monkeypatch.setattr(
        pipeline_job,
        "embed_observations",
        AsyncMock(side_effect=TimeoutError("embedding timed out")),
    )

    with pytest.raises(TimeoutError, match="embedding timed out"):
        await pipeline_job.process_candidate_job(
            {"session_factory": object(), "settings": _settings()},
            str(person_id),
            str(job.id),
        )

    assert job.status == "failed"
    assert job.result is not None
    assert job.result["failure_kind"] == "transient"
    assert job.result["retryable"] is True


@pytest.mark.asyncio
async def test_processing_terminal_duplicate_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    person_id = uuid.uuid4()
    job = JobRun(
        id=uuid.uuid4(),
        job_type="process_candidate",
        status="succeeded",
        phase="complete",
        attempt=3,
        result={"person_id": str(person_id), "status": "succeeded"},
    )
    session = _session_for(SimpleNamespace(id=person_id), job)
    _patch_session(monkeypatch, session)
    reconcile = AsyncMock()
    monkeypatch.setattr(pipeline_job, "reconcile_observations", reconcile)

    result = await pipeline_job.process_candidate_job(
        {"session_factory": object(), "settings": _settings()}, str(person_id), str(job.id)
    )

    assert result == job.result
    reconcile.assert_not_awaited()


@pytest.mark.asyncio
async def test_processing_failed_job_retries_with_incremented_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    person_id = uuid.uuid4()
    job = JobRun(
        id=uuid.uuid4(),
        job_type="process_candidate",
        status="failed",
        phase="processing",
        attempt=2,
    )
    session = _session_for(SimpleNamespace(id=person_id), job)
    _patch_session(monkeypatch, session)
    _patch_pipeline(monkeypatch)

    result = await pipeline_job.process_candidate_job(
        {"session_factory": object(), "settings": _settings()}, str(person_id), str(job.id)
    )

    assert result["claims_created"] == 2
    assert job.status == "succeeded"
    assert job.attempt == 3
