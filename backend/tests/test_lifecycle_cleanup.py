"""Tests for application and worker resource cleanup."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app import main, worker


@pytest.mark.asyncio
async def test_api_lifespan_closes_storage_and_database(monkeypatch: pytest.MonkeyPatch) -> None:
    close_storage = AsyncMock()
    close_ai = AsyncMock()
    dispose_engine = AsyncMock()
    monkeypatch.setattr(main, "close_client", close_storage)
    monkeypatch.setattr(main, "close_clients", close_ai)
    monkeypatch.setattr(main, "get_engine", lambda: SimpleNamespace(dispose=dispose_engine))

    async with main.lifespan(main.app):
        pass

    close_storage.assert_awaited_once()
    close_ai.assert_awaited_once()
    dispose_engine.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_shutdown_closes_storage_and_database(monkeypatch: pytest.MonkeyPatch) -> None:
    close_storage = AsyncMock()
    close_ai = AsyncMock()
    dispose_engine = AsyncMock()
    monkeypatch.setattr(worker, "close_client", close_storage)
    monkeypatch.setattr(worker, "close_clients", close_ai)
    monkeypatch.setattr(worker, "get_engine", lambda: SimpleNamespace(dispose=dispose_engine))

    await worker.shutdown({})

    close_storage.assert_awaited_once()
    close_ai.assert_awaited_once()
    dispose_engine.assert_awaited_once()
