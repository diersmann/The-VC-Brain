"""Session dependency lifecycle tests without requiring PostgreSQL."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.db import session as session_module


class _TrackedSession:
    def __init__(self, tracker: dict[str, int]) -> None:
        self.tracker = tracker
        self.closed = False
        self.rolled_back = False

    async def __aenter__(self) -> _TrackedSession:
        self.tracker["active"] += 1
        self.tracker["opened"] += 1
        return self

    async def __aexit__(self, *_args: object) -> None:
        self.closed = True
        self.tracker["active"] -= 1

    async def rollback(self) -> None:
        self.rolled_back = True


def _factory(tracker: dict[str, int]) -> Any:
    def make_session() -> _TrackedSession:
        return _TrackedSession(tracker)

    return make_session


@pytest.mark.asyncio
async def test_concurrent_sessions_close_and_return_to_baseline(monkeypatch) -> None:
    tracker = {"active": 0, "opened": 0}
    monkeypatch.setattr(session_module, "_get_session_factory", lambda: _factory(tracker))

    async def use_session() -> None:
        async with session_module.session_context() as session:
            assert session.closed is False
            await asyncio.sleep(0)

    await asyncio.gather(*(use_session() for _ in range(8)))

    assert tracker == {"active": 0, "opened": 8}


@pytest.mark.asyncio
async def test_session_rolls_back_and_closes_after_dependency_error(monkeypatch) -> None:
    tracker = {"active": 0, "opened": 0}
    created: list[_TrackedSession] = []

    def make_session() -> _TrackedSession:
        session = _TrackedSession(tracker)
        created.append(session)
        return session

    monkeypatch.setattr(session_module, "_get_session_factory", lambda: make_session)

    dependency = session_module.get_session()
    await anext(dependency)
    with pytest.raises(RuntimeError, match="boom"):
        await dependency.athrow(RuntimeError("boom"))

    assert created[0].rolled_back is True
    assert created[0].closed is True
    assert tracker["active"] == 0
