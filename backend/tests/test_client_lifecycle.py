"""Tests for process-owned AI and request-scoped Redis clients."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest

from app.client_lifecycle import close_clients, get_openai_client, redis_connection


class _FakeOpenAI:
    def __init__(self, *, api_key: str, **_: str) -> None:
        self.api_key = api_key
        self.close = AsyncMock()


@pytest.fixture(autouse=True)
async def _clean_registry() -> AsyncIterator[None]:
    await close_clients()
    yield
    await close_clients()


@pytest.mark.asyncio
async def test_openai_client_is_reused_for_matching_configuration() -> None:
    created: list[_FakeOpenAI] = []

    def factory(**kwargs: str) -> _FakeOpenAI:
        client = _FakeOpenAI(**kwargs)
        created.append(client)
        return client

    first = await get_openai_client("test-key", factory=factory)
    second = await get_openai_client("test-key", factory=factory, base_url="")

    assert first is second
    assert len(created) == 1


@pytest.mark.asyncio
async def test_close_clients_closes_each_owned_client_once() -> None:
    created: list[_FakeOpenAI] = []

    def factory(**kwargs: str) -> _FakeOpenAI:
        client = _FakeOpenAI(**kwargs)
        created.append(client)
        return client

    await get_openai_client("first", factory=factory)
    await get_openai_client("second", factory=factory)

    await close_clients()
    await close_clients()

    assert [client.close.await_count for client in created] == [1, 1]


@pytest.mark.asyncio
async def test_close_clients_deduplicates_shared_factory_objects() -> None:
    client = _FakeOpenAI(api_key="shared")

    def factory(**_: str) -> _FakeOpenAI:
        return client

    await get_openai_client("first", factory=factory)
    await get_openai_client("second", factory=factory)

    await close_clients()

    client.close.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_failed_close_is_retried_on_next_shutdown() -> None:
    client = _FakeOpenAI(api_key="transient")
    client.close = AsyncMock(side_effect=[RuntimeError("temporary"), None])

    def factory(**_: str) -> _FakeOpenAI:
        return client

    await get_openai_client("transient", factory=factory)
    with pytest.raises(RuntimeError, match="temporary"):
        await close_clients()

    await close_clients()
    assert client.close.await_count == 2


@pytest.mark.asyncio
async def test_cancelled_close_is_retried_on_next_shutdown() -> None:
    client = _FakeOpenAI(api_key="cancelled")
    client.close = AsyncMock(side_effect=[asyncio.CancelledError(), None])

    def factory(**_: str) -> _FakeOpenAI:
        return client

    await get_openai_client("cancelled", factory=factory)
    with pytest.raises(asyncio.CancelledError):
        await close_clients()

    await close_clients()
    assert client.close.await_count == 2


@pytest.mark.asyncio
async def test_get_rejected_while_close_is_in_progress() -> None:
    close_started = asyncio.Event()
    allow_close = asyncio.Event()
    created: list[_FakeOpenAI] = []

    async def close() -> None:
        close_started.set()
        await allow_close.wait()

    def factory(**kwargs: str) -> _FakeOpenAI:
        client = _FakeOpenAI(**kwargs)
        client.close = AsyncMock(side_effect=close)
        created.append(client)
        return client

    await get_openai_client("test-key", factory=factory)
    closing = asyncio.create_task(close_clients())
    await close_started.wait()

    with pytest.raises(RuntimeError, match="registry is closing"):
        await get_openai_client("test-key", factory=factory)

    allow_close.set()
    await closing
    replacement = await get_openai_client("test-key", factory=factory)
    assert replacement is not created[0]
    await close_clients()


@pytest.mark.asyncio
async def test_redis_connection_closes_on_body_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import redis.asyncio as aioredis

    redis = AsyncMock()
    monkeypatch.setattr(aioredis, "from_url", lambda *_args, **_kwargs: redis)

    with pytest.raises(RuntimeError, match="body failed"):
        async with redis_connection():
            raise RuntimeError("body failed")

    redis.aclose.assert_awaited_once_with()
