"""Process client ownership and deterministic close helpers.

The API keeps Redis connections request-scoped so a failed request cannot leave
an idle pool behind.  AI clients are different: they are safe to reuse for the
life of a process, so this module owns one client per provider credential and
closes all of them from the API/worker lifecycle hooks.

This module deliberately does not create clients eagerly.  Local startup and
tests therefore do not require provider credentials or network access.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

import structlog
from openai import AsyncOpenAI

logger = structlog.get_logger(__name__)

OpenAIClient = Any
OpenAIFactory = Callable[..., OpenAIClient]


class _ClientRegistry:
    """Own process-scoped clients and close each object at most once."""

    def __init__(self) -> None:
        self._clients: dict[tuple[int, str, str | None, str | None], OpenAIClient] = {}
        self._factories: dict[int, OpenAIFactory] = {}
        self._lock = asyncio.Lock()
        self._closing = False
        self._close_finished: asyncio.Event | None = None

    async def get_openai(
        self,
        api_key: str,
        *,
        factory: OpenAIFactory = AsyncOpenAI,
        base_url: str | None = None,
        organization: str | None = None,
    ) -> OpenAIClient:
        """Return a shared OpenAI client for one credential/configuration.

        ``factory`` is part of the key so tests can inject a provider without
        sharing the production client instance.  No key or credential is ever
        logged.
        """
        # Factories are dependency-injection seams (and may be unhashable
        # callable instances), so key by identity rather than by object hash.
        base_url = base_url or None
        organization = organization or None
        key = (id(factory), api_key, base_url, organization)
        async with self._lock:
            if self._closing:
                raise RuntimeError("OpenAI client registry is closing")
            existing = self._clients.get(key)
            if existing is not None:
                return existing

            kwargs: dict[str, str] = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            if organization:
                kwargs["organization"] = organization
            client = factory(**kwargs)
            self._clients[key] = client
            self._factories.setdefault(id(factory), factory)
            return client

    async def close(self) -> None:
        """Close every owned client, continuing after an individual failure."""
        entries: tuple[
            tuple[tuple[int, str, str | None, str | None], OpenAIClient], ...
        ] = ()
        factories: dict[int, OpenAIFactory] = {}
        async with self._lock:
            if self._closing:
                finished = self._close_finished
                owner = False
                clients: tuple[OpenAIClient, ...] = ()
            else:
                self._closing = True
                finished = asyncio.Event()
                self._close_finished = finished
                owner = True
                # A dependency-injected factory may intentionally return one
                # object for multiple configurations; never close that object
                # more than once during a shutdown pass.
                entries = tuple(self._clients.items())
                factories = dict(self._factories)
                clients = tuple({id(client): client for _, client in entries}.values())
                self._clients.clear()
                self._factories.clear()

        if not owner:
            # A second shutdown caller waits for the first one, rather than
            # returning while provider sockets are still being released.
            if finished is not None:
                await finished.wait()
            return

        first_error: BaseException | None = None
        failed_ids: set[int] = set()
        try:
            for client in clients:
                close = getattr(client, "close", None)
                if close is None:
                    continue
                try:
                    result = close()
                    if inspect.isawaitable(result):
                        await result
                except BaseException as exc:  # pragma: no cover - provider-specific failure
                    failed_ids.add(id(client))
                    if first_error is None:
                        first_error = exc
                    logger.warning("client_close_failed", client_type=type(client).__name__)
        finally:
            async with self._lock:
                if failed_ids:
                    self._clients = {
                        key: client
                        for key, client in entries
                        if id(client) in failed_ids
                    }
                    failed_factory_ids = {
                        key[0] for key, client in entries if id(client) in failed_ids
                    }
                    self._factories = {
                        factory_id: factory
                        for factory_id, factory in factories.items()
                        if factory_id in failed_factory_ids
                    }
                self._closing = False
                if finished is not None:
                    finished.set()
                self._close_finished = None

        if first_error is not None:
            raise first_error


_registry = _ClientRegistry()


async def get_openai_client(
    api_key: str,
    *,
    factory: OpenAIFactory = AsyncOpenAI,
    base_url: str | None = None,
    organization: str | None = None,
) -> OpenAIClient:
    """Get a process-owned OpenAI client without making network calls."""
    return await _registry.get_openai(
        api_key,
        factory=factory,
        base_url=base_url,
        organization=organization,
    )


async def close_clients() -> None:
    """Close all process-owned AI clients; safe to call repeatedly."""
    await _registry.close()


@asynccontextmanager
async def redis_connection(*, decode_responses: bool = True) -> AsyncIterator[Any]:
    """Yield one request-scoped Redis client and always close it."""
    import redis.asyncio as aioredis

    from app.config import get_settings

    client = aioredis.from_url(  # type: ignore[no-untyped-call]
        get_settings().redis_url,
        decode_responses=decode_responses,
    )
    try:
        yield client
    finally:
        await client.aclose()
