"""Tests for the Redis-backed priority queue.

Uses fakeredis to avoid requiring a real Redis server.
"""

from __future__ import annotations

from typing import Any

import pytest
from fakeredis import FakeAsyncRedis

from app.collectors.queue import (
    clear_all,
    enqueue,
    peek,
    pop_top,
    queue_depth,
)


@pytest.fixture
async def redis() -> Any:
    r = FakeAsyncRedis(decode_responses=True)
    yield r
    await r.flushall()


@pytest.mark.asyncio
async def test_enqueue_and_pop_top(redis: Any) -> None:
    """Enqueue a task and pop it back."""
    task = {"person_id": "abc", "source": "github", "depth": "deep"}
    await enqueue(redis, task, priority=5.0)
    popped = await pop_top(redis, n=1)
    assert len(popped) == 1
    assert popped[0] == task


@pytest.mark.asyncio
async def test_pop_top_respects_priority(redis: Any) -> None:
    """Higher priority tasks should be popped first."""
    await enqueue(redis, {"id": "low"}, priority=1.0)
    await enqueue(redis, {"id": "high"}, priority=10.0)
    await enqueue(redis, {"id": "medium"}, priority=5.0)

    popped = await pop_top(redis, n=3)
    assert len(popped) == 3
    assert popped[0]["id"] == "high"
    assert popped[1]["id"] == "medium"
    assert popped[2]["id"] == "low"


@pytest.mark.asyncio
async def test_pop_top_empty_queue(redis: Any) -> None:
    """Popping from an empty queue should return an empty list."""
    popped = await pop_top(redis, n=5)
    assert popped == []


@pytest.mark.asyncio
async def test_peek_does_not_remove(redis: Any) -> None:
    """Peek should return tasks without removing them."""
    await enqueue(redis, {"id": "task1"}, priority=5.0)
    await enqueue(redis, {"id": "task2"}, priority=3.0)

    peeked = await peek(redis, n=2)
    assert len(peeked) == 2

    # Queue should still have both tasks
    depths = await queue_depth(redis)
    assert sum(depths.values()) == 2


@pytest.mark.asyncio
async def test_queue_depth(redis: Any) -> None:
    """Queue depth should report correct counts per lane."""
    await enqueue(redis, {"id": "high"}, priority=10.0)
    await enqueue(redis, {"id": "normal"}, priority=5.0)
    await enqueue(redis, {"id": "low"}, priority=0.5)

    depths = await queue_depth(redis)
    assert sum(depths.values()) == 3


@pytest.mark.asyncio
async def test_clear_all(redis: Any) -> None:
    """Clear all should remove all tasks."""
    await enqueue(redis, {"id": "task"}, priority=5.0)
    await clear_all(redis)
    depths = await queue_depth(redis)
    assert sum(depths.values()) == 0


@pytest.mark.asyncio
async def test_deduplication(redis: Any) -> None:
    """Same task in the same lane should not be duplicated (score updated instead)."""
    task = {"id": "unique"}
    await enqueue(redis, task, priority=5.0)
    await enqueue(redis, task, priority=5.0)

    depths = await queue_depth(redis)
    assert sum(depths.values()) == 1, "Duplicate task in same lane should not increase queue depth"


@pytest.mark.asyncio
async def test_different_lanes_for_different_priorities(redis: Any) -> None:
    """Same task with different priority may land in different lanes."""
    task = {"id": "unique"}
    await enqueue(redis, task, priority=1.0)  # normal lane
    await enqueue(redis, task, priority=10.0)  # high lane

    depths = await queue_depth(redis)
    # Two lanes each have one entry (different lanes, different scores)
    assert sum(depths.values()) == 2, "Different priority lanes are separate queues"
