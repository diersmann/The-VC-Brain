"""Tests for dependency-aware readiness and worker liveness markers."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.routes import health
from app.worker import worker_heartbeat


@pytest.mark.asyncio
async def test_readiness_reports_all_dependencies_when_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health, "_check_postgres", AsyncMock())
    monkeypatch.setattr(health, "_check_redis", AsyncMock())
    monkeypatch.setattr(health, "_check_storage", AsyncMock())

    response = await health.readiness()

    assert response.status == "ready"
    assert response.dependencies == {"postgres": "ok", "redis": "ok", "minio": "ok"}


@pytest.mark.asyncio
async def test_readiness_returns_503_for_failed_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "_check_postgres", AsyncMock())
    monkeypatch.setattr(health, "_check_redis", AsyncMock(side_effect=RuntimeError("down")))
    monkeypatch.setattr(health, "_check_storage", AsyncMock())

    with pytest.raises(HTTPException) as error:
        await health.readiness()

    assert error.value.status_code == 503
    assert error.value.detail == {"status": "not_ready", "failed_dependencies": ["redis"]}


@pytest.mark.asyncio
async def test_worker_heartbeat_sets_expiring_marker() -> None:
    redis = AsyncMock()

    await worker_heartbeat({"redis": redis})

    redis.set.assert_awaited_once()
    assert redis.set.await_args.kwargs["ex"] == 120
