"""Durable connector success watermark coverage."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.dialects.postgresql import dialect

from app.api.routes import collection
from app.collectors import jobs
from app.collectors.base import Collected
from app.collectors.registry import _BUILTIN
from app.collectors.telemetry import record_connector_success
from app.db.models import JobRun


@pytest.mark.asyncio
async def test_record_connector_success_upserts_a_monotonic_watermark() -> None:
    session = AsyncMock()
    occurred_at = datetime(2026, 8, 7, 12, 34, 56)

    await record_connector_success(session, "github", occurred_at=occurred_at)

    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(dialect=dialect()))
    assert "INSERT INTO connector_telemetry" in sql
    assert "ON CONFLICT (source_type) DO UPDATE" in sql
    assert "greatest" in sql.lower()
    params = statement.compile(dialect=dialect()).params
    assert params["source_type"] == "github"
    assert params["last_success_at"].tzinfo == UTC


@pytest.mark.asyncio
async def test_record_connector_success_rejects_blank_source_without_writing() -> None:
    session = AsyncMock()

    with pytest.raises(ValueError, match="source_type"):
        await record_connector_success(session, " ")

    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_collection_health_exposes_persisted_timestamp_without_health_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registered = {source_type for source_type, _module, _class in _BUILTIN}
    timestamp = datetime(2026, 8, 7, 12, 34, 56, tzinfo=UTC)
    telemetry = SimpleNamespace(source_type="github", last_success_at=timestamp)
    result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [telemetry]))
    session = AsyncMock()
    session.execute.return_value = result
    monkeypatch.setattr(collection, "queue_depth", AsyncMock(return_value={"collect": 0}))
    monkeypatch.setattr(
        collection,
        "all_connectors",
        lambda: {name: SimpleNamespace() for name in registered},
    )

    response = await collection.collection_health(object(), session)

    assert response.connector_readiness["github"].last_success_at == timestamp.isoformat()
    assert response.connector_readiness["producthunt"].last_success_at is None


@pytest.mark.asyncio
async def test_collection_health_keeps_static_projection_when_telemetry_read_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registered = {source_type for source_type, _module, _class in _BUILTIN}
    session = AsyncMock()
    session.execute.side_effect = RuntimeError("database unavailable")
    monkeypatch.setattr(collection, "queue_depth", AsyncMock(return_value={"collect": 0}))
    monkeypatch.setattr(
        collection,
        "all_connectors",
        lambda: {name: SimpleNamespace() for name in registered},
    )

    response = await collection.collection_health(object(), session)

    assert response.connector_readiness["github"].last_success_at is None
    assert set(response.connectors) == registered


@pytest.mark.asyncio
async def test_failed_collection_persistence_does_not_record_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    person_id = uuid.uuid4()
    job = JobRun(id=uuid.uuid4(), job_type="collect", attempt=0)
    person = SimpleNamespace(
        id=person_id,
        handles={"github": "founder"},
        display_name="Founder",
    )
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: person)

    async def get(model: object, _job_id: object) -> JobRun | None:
        return job if model is JobRun else None

    session.get.side_effect = get

    @asynccontextmanager
    async def session_context(_ctx: dict[str, object]):
        yield session

    monkeypatch.setattr(jobs, "_session_ctx", session_context)
    monkeypatch.setattr(
        jobs,
        "get_connector",
        lambda _source: SimpleNamespace(
            collect=AsyncMock(
                return_value=Collected(
                    content=b"snapshot",
                    content_type="text/plain",
                    observations=[],
                    source_type="github",
                    uri="https://github.example/profile",
                )
            )
        ),
    )
    monkeypatch.setattr(
        jobs,
        "_write_snapshot",
        AsyncMock(side_effect=RuntimeError("database unavailable")),
    )
    record = AsyncMock()
    monkeypatch.setattr(jobs, "record_connector_success", record)

    with pytest.raises(RuntimeError, match="database unavailable"):
        await jobs.collect_job(
            {"session_factory": object()}, str(person_id), "github", job_id=str(job.id)
        )

    record.assert_not_awaited()
