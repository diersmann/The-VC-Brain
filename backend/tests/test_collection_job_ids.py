"""API queue-entry coverage for caller-visible collection JobRun IDs."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import collection
from app.collectors import queue as queue_module
from app.db.models import JobRun


def _job(job_type: str) -> JobRun:
    return JobRun(id=uuid.uuid4(), job_type=job_type, status="queued", phase="queued")


def _session() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.mark.asyncio
async def test_identity_resolve_returns_job_id_and_forwards_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    redis = object()
    job = _job("resolve_identities")
    enqueue = AsyncMock()
    create = AsyncMock(return_value=job)
    monkeypatch.setattr(queue_module, "enqueue", enqueue)
    monkeypatch.setattr(collection, "create_job", create)

    response = await collection.trigger_identity_resolve(redis, session)

    assert response.job_id == str(job.id)
    enqueue.assert_awaited_once_with(
        redis, {"job_type": "resolve_identities", "job_id": str(job.id)}, priority=10.0
    )
    create.assert_awaited_once_with(session, "resolve_identities")
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_identity_resolve_marks_job_failed_when_queue_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    job = _job("resolve_identities")
    monkeypatch.setattr(queue_module, "enqueue", AsyncMock(side_effect=RuntimeError("redis down")))
    monkeypatch.setattr(collection, "create_job", AsyncMock(return_value=job))
    update = AsyncMock()
    monkeypatch.setattr(collection, "update_job", update)

    with pytest.raises(HTTPException) as error:
        await collection.trigger_identity_resolve(object(), session)

    assert error.value.status_code == 503
    update.assert_awaited_once_with(
        session,
        job.id,
        status="failed",
        phase="queue",
        last_error="redis down",
        result={"error": "queue_failed"},
    )
    assert session.commit.await_count == 2


@pytest.mark.asyncio
async def test_processing_returns_job_id_and_forwards_task(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    candidate_id = uuid.uuid4()
    redis = object()
    session.get.return_value = SimpleNamespace(id=candidate_id, canonical=True)
    job = _job("process_candidate")
    enqueue = AsyncMock()
    monkeypatch.setattr(queue_module, "enqueue", enqueue)
    monkeypatch.setattr(collection, "create_job", AsyncMock(return_value=job))

    response = await collection.process_candidate_route(candidate_id, redis, session)

    assert response.job_id == str(job.id)
    enqueue.assert_awaited_once_with(
        redis,
        {
            "job_type": "process_candidate",
            "person_id": str(candidate_id),
            "job_id": str(job.id),
        },
        priority=5.0,
    )


@pytest.mark.asyncio
async def test_processing_marks_job_failed_when_queue_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    candidate_id = uuid.uuid4()
    session.get.return_value = SimpleNamespace(id=candidate_id, canonical=True)
    job = _job("process_candidate")
    monkeypatch.setattr(queue_module, "enqueue", AsyncMock(side_effect=RuntimeError("redis down")))
    monkeypatch.setattr(collection, "create_job", AsyncMock(return_value=job))
    update = AsyncMock()
    monkeypatch.setattr(collection, "update_job", update)

    with pytest.raises(HTTPException) as error:
        await collection.process_candidate_route(candidate_id, object(), session)

    assert error.value.status_code == 503
    update.assert_awaited_once_with(
        session,
        job.id,
        status="failed",
        phase="queue",
        last_error="redis down",
        result={"error": "queue_failed"},
    )
    assert session.commit.await_count == 2


@pytest.mark.asyncio
async def test_avatar_batch_returns_job_ids_and_forwards_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    person_id = uuid.uuid4()
    person = SimpleNamespace(id=person_id)
    result = MagicMock()
    result.scalars.return_value.all.return_value = [person]
    session.execute.return_value = result
    monkeypatch.setattr(
        collection, "_current_opportunity", AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4()))
    )
    job = _job("fetch_candidate_avatar")
    enqueue = AsyncMock()
    monkeypatch.setattr(queue_module, "enqueue", enqueue)
    monkeypatch.setattr(collection, "create_job", AsyncMock(return_value=job))

    response = await collection.fetch_candidate_avatars(
        collection.AvatarBatchRequest(candidate_ids=[str(person_id)]), object(), session
    )

    assert response.job_ids == [str(job.id)]
    assert response.candidate_ids == [str(person_id)]
    task = enqueue.await_args.args[1]
    assert task == {
        "job_type": "fetch_candidate_avatar",
        "person_id": str(person_id),
        "source": "avatar",
        "job_id": str(job.id),
    }
    assert enqueue.await_args.kwargs == {"priority": 10.0}
    assert session.commit.await_count == 2


@pytest.mark.asyncio
async def test_avatar_batch_marks_queue_failure_and_excludes_failed_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    person_id = uuid.uuid4()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [SimpleNamespace(id=person_id)]
    session.execute.return_value = result
    monkeypatch.setattr(
        collection, "_current_opportunity", AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4()))
    )
    job = _job("fetch_candidate_avatar")
    monkeypatch.setattr(
        queue_module, "enqueue", AsyncMock(side_effect=RuntimeError("redis down"))
    )
    monkeypatch.setattr(collection, "create_job", AsyncMock(return_value=job))
    update = AsyncMock()
    monkeypatch.setattr(collection, "update_job", update)

    response = await collection.fetch_candidate_avatars(
        collection.AvatarBatchRequest(candidate_ids=[str(person_id)]), object(), session
    )

    assert response.queued == 0
    assert response.candidate_ids == []
    assert response.job_ids == []
    update.assert_awaited_once_with(
        session,
        job.id,
        status="failed",
        phase="queue",
        last_error="redis down",
        result={"error": "queue_failed"},
    )
    assert session.commit.await_count == 2


@pytest.mark.asyncio
async def test_avatar_batch_keeps_successful_jobs_when_one_enqueue_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    first_id, second_id = uuid.uuid4(), uuid.uuid4()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        SimpleNamespace(id=first_id),
        SimpleNamespace(id=second_id),
    ]
    session.execute.return_value = result
    monkeypatch.setattr(
        collection,
        "_current_opportunity",
        AsyncMock(side_effect=[SimpleNamespace(id=uuid.uuid4()), SimpleNamespace(id=uuid.uuid4())]),
    )
    first_job, second_job = _job("fetch_candidate_avatar"), _job("fetch_candidate_avatar")
    monkeypatch.setattr(collection, "create_job", AsyncMock(side_effect=[first_job, second_job]))
    monkeypatch.setattr(
        queue_module,
        "enqueue",
        AsyncMock(side_effect=[RuntimeError("redis down"), None]),
    )
    update = AsyncMock()
    monkeypatch.setattr(collection, "update_job", update)

    response = await collection.fetch_candidate_avatars(
        collection.AvatarBatchRequest(candidate_ids=[str(first_id), str(second_id)]),
        object(),
        session,
    )

    assert response.queued == 1
    assert response.candidate_ids == [str(second_id)]
    assert response.job_ids == [str(second_job.id)]
    update.assert_awaited_once_with(
        session,
        first_job.id,
        status="failed",
        phase="queue",
        last_error="redis down",
        result={"error": "queue_failed"},
    )
