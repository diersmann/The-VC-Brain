"""Concurrency and ownership tests for the MinIO client lifecycle."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import pytest

from app import storage


class _ClientError(Exception):
    def __init__(self, code: str) -> None:
        self.response = {"Error": {"Code": code}}
        super().__init__(code)


class _FakeClient:
    exceptions = SimpleNamespace(ClientError=_ClientError)

    def __init__(self) -> None:
        self.head_bucket_calls = 0
        self.create_bucket_calls = 0
        self.close_calls = 0
        self.head_bucket_error: str | None = None
        self.create_bucket_error: str | None = None
        self.head_bucket_started: asyncio.Event | None = None
        self.allow_head_bucket: asyncio.Event | None = None

    async def head_bucket(self, **_: Any) -> None:
        self.head_bucket_calls += 1
        if self.head_bucket_started is not None:
            self.head_bucket_started.set()
        if self.allow_head_bucket is not None:
            await self.allow_head_bucket.wait()
        if self.head_bucket_error is not None:
            raise _ClientError(self.head_bucket_error)

    async def create_bucket(self, **_: Any) -> None:
        self.create_bucket_calls += 1
        if self.create_bucket_error is not None:
            raise _ClientError(self.create_bucket_error)

    async def __aexit__(self, *_: Any) -> None:
        self.close_calls += 1


class _FakeClientContext:
    def __init__(self, client: _FakeClient) -> None:
        self.client = client
        self.enter_calls = 0
        self.exit_calls = 0

    async def __aenter__(self) -> _FakeClient:
        self.enter_calls += 1
        return self.client

    async def __aexit__(self, *_: Any) -> None:
        self.exit_calls += 1


class _FakeSession:
    def __init__(self, context: _FakeClientContext) -> None:
        self.context = context
        self.client_calls = 0

    def client(self, *_: Any, **__: Any) -> _FakeClientContext:
        self.client_calls += 1
        return self.context


@pytest.fixture(autouse=True)
async def _reset_storage() -> AsyncIterator[None]:
    await storage.close_client()
    yield
    await storage.close_client()


def _patch_storage_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    session: _FakeSession,
) -> None:
    import aioboto3  # type: ignore[import-untyped]

    monkeypatch.setattr(aioboto3, "Session", lambda: session)
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: SimpleNamespace(
            minio_endpoint="minio:9000",
            minio_access_key="access",
            minio_secret_key="secret",
            minio_bucket="snapshots",
            minio_secure=False,
        ),
    )


@pytest.mark.asyncio
async def test_concurrent_first_requests_share_one_initialized_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeClient()
    client.head_bucket_started = asyncio.Event()
    client.allow_head_bucket = asyncio.Event()
    context = _FakeClientContext(client)
    session = _FakeSession(context)
    _patch_storage_dependencies(monkeypatch, session)

    first = asyncio.create_task(storage._get_client())
    await client.head_bucket_started.wait()
    second = asyncio.create_task(storage._get_client())
    await asyncio.sleep(0)
    client.allow_head_bucket.set()

    first_client, second_client = await asyncio.gather(first, second)

    assert first_client is client
    assert second_client is client
    assert session.client_calls == 1
    assert context.enter_calls == 1
    assert client.head_bucket_calls == 1


@pytest.mark.asyncio
async def test_bucket_creation_conflict_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeClient()
    client.head_bucket_error = "404"
    client.create_bucket_error = "BucketAlreadyOwnedByYou"
    context = _FakeClientContext(client)
    session = _FakeSession(context)
    _patch_storage_dependencies(monkeypatch, session)

    assert await storage._get_client() is client
    assert client.head_bucket_calls == 1
    assert client.create_bucket_calls == 1
    assert storage._bucket_ensured is True


@pytest.mark.asyncio
async def test_bucket_creation_conflict_for_other_owner_is_not_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeClient()
    client.head_bucket_error = "404"
    client.create_bucket_error = "BucketAlreadyExists"
    context = _FakeClientContext(client)
    session = _FakeSession(context)
    _patch_storage_dependencies(monkeypatch, session)

    with pytest.raises(_ClientError, match="BucketAlreadyExists"):
        await storage._get_client()
    assert storage._client is None
    assert context.exit_calls == 1


@pytest.mark.asyncio
async def test_failed_initialization_closes_entered_context_and_can_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_client = _FakeClient()
    first_client.head_bucket_error = "AccessDenied"
    first_context = _FakeClientContext(first_client)
    first_session = _FakeSession(first_context)
    _patch_storage_dependencies(monkeypatch, first_session)

    with pytest.raises(_ClientError, match="AccessDenied"):
        await storage._get_client()

    assert storage._client is None
    assert first_context.enter_calls == 1
    assert first_context.exit_calls == 1

    first_client.head_bucket_error = None
    assert await storage._get_client() is first_client
    assert first_context.enter_calls == 2


@pytest.mark.asyncio
async def test_concurrent_close_has_one_owner_and_get_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeClient()
    context = _FakeClientContext(client)
    session = _FakeSession(context)
    _patch_storage_dependencies(monkeypatch, session)
    await storage._get_client()

    close_started = asyncio.Event()
    allow_close = asyncio.Event()

    async def slow_close(*_: Any) -> None:
        close_started.set()
        await allow_close.wait()
        context.exit_calls += 1

    client.__aexit__ = slow_close  # type: ignore[method-assign]
    first_close = asyncio.create_task(storage.close_client())
    await close_started.wait()
    second_close = asyncio.create_task(storage.close_client())
    await asyncio.sleep(0)

    with pytest.raises(RuntimeError, match="storage client is closing"):
        await storage._get_client()
    assert not second_close.done()

    allow_close.set()
    await asyncio.gather(first_close, second_close)
    assert context.exit_calls == 1
    assert storage._client is None


@pytest.mark.asyncio
async def test_failed_close_preserves_client_for_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeClient()
    context = _FakeClientContext(client)
    session = _FakeSession(context)
    _patch_storage_dependencies(monkeypatch, session)
    await storage._get_client()

    close_attempts = 0

    async def flaky_close(*_: Any) -> None:
        nonlocal close_attempts
        close_attempts += 1
        if close_attempts == 1:
            raise RuntimeError("temporary")

    client.__aexit__ = flaky_close  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="temporary"):
        await storage.close_client()
    assert storage._client is client

    await storage.close_client()
    assert close_attempts == 2
    assert storage._client is None
