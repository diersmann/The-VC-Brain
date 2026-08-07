"""Redis-backed priority queue for collection tasks.

Uses three sorted sets (high / normal / low) so the dispatcher can
respect priority lanes.  Score = negative priority (lower = first).
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from redis.exceptions import WatchError

logger = structlog.get_logger(__name__)

# Redis key prefixes
_PREFIX = "vcbrain:collect"
_QUEUE_KEYS = {
    "high": f"{_PREFIX}:high",
    "normal": f"{_PREFIX}:normal",
    "low": f"{_PREFIX}:low",
}

# Budget counter for Tavily
_TAVILY_BUDGET_KEY = "vcbrain:budget:tavily"
# Page tracker for auto-advancing discovery queries
_PAGE_PREFIX = "vcbrain:page:"
_MAX_DISCOVERY_PAGE = 10


def _lane(priority: float) -> str:
    if priority >= 10.0:
        return "high"
    if priority >= 1.0:
        return "normal"
    return "low"


def _task_key(task: dict[str, Any]) -> str:
    """Deterministic key for deduplication within the queue."""
    return json.dumps(task, sort_keys=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def enqueue(
    redis: Any,
    task: dict[str, Any],
    priority: float,
) -> None:
    """Push a task into the appropriate priority lane.

    If a task with the same key already exists, it is *not* duplicated
    (the existing entry's score is updated instead).
    """
    lane = _lane(priority)
    key = _QUEUE_KEYS[lane]
    member = _task_key(task)
    # Score = negative priority so ZRANGEBYSCORE ... 0 returns highest first
    score = -priority

    await redis.zadd(key, {member: score})
    logger.debug("queue_enqueued", lane=lane, priority=round(priority, 2), task=task)


async def pop_top(
    redis: Any,
    n: int = 1,
) -> list[dict[str, Any]]:
    """Pop the *n* highest-priority tasks across all lanes.

    Lanes are checked in order: high → normal → low.
    Returns an empty list when the queue is empty.
    """
    tasks_with_priority = await pop_top_with_priority(redis, n)
    return [task for task, _priority in tasks_with_priority]


async def pop_top_with_priority(
    redis: Any,
    n: int = 1,
) -> list[tuple[dict[str, Any], float]]:
    """Pop tasks while retaining their priority for safe requeue."""
    tasks: list[tuple[dict[str, Any], float]] = []
    for lane in ("high", "normal", "low"):
        if len(tasks) >= n:
            break
        key = _QUEUE_KEYS[lane]
        # Pop the lowest score (highest priority) member
        results = await redis.zpopmin(key, count=n - len(tasks))
        for member, score in results:
            tasks.append((json.loads(member), -float(score)))
    return tasks


async def peek(
    redis: Any,
    n: int = 5,
) -> list[dict[str, Any]]:
    """Return the next *n* tasks without removing them."""
    tasks: list[dict[str, Any]] = []
    for lane in ("high", "normal", "low"):
        if len(tasks) >= n:
            break
        key = _QUEUE_KEYS[lane]
        results = await redis.zrange(key, 0, n - len(tasks) - 1, withscores=True)
        for member, _score in results:
            tasks.append(json.loads(member))
    return tasks


async def queue_depth(redis: Any) -> dict[str, int]:
    """Return the number of pending tasks per lane."""
    depths: dict[str, int] = {}
    for lane, key in _QUEUE_KEYS.items():
        depths[lane] = await redis.zcard(key)
    return depths


async def clear_all(redis: Any) -> None:
    """Remove all tasks from all lanes (used in tests)."""
    for key in _QUEUE_KEYS.values():
        await redis.delete(key)


# ---------------------------------------------------------------------------
# Tavily budget counter
# ---------------------------------------------------------------------------


async def get_tavily_budget_remaining(redis: Any) -> int:
    """Return remaining Tavily API calls for the current month."""
    val = await redis.get(_TAVILY_BUDGET_KEY)
    return int(val) if val else 0


async def decrement_tavily_budget(redis: Any, amount: int = 1) -> int:
    """Decrement the Tavily budget counter and return the new value."""
    result: int = await redis.decrby(_TAVILY_BUDGET_KEY, amount)
    return result


async def reset_tavily_budget(redis: Any, monthly_limit: int) -> None:
    """Set the Tavily budget counter (called on first-of-month or startup)."""
    await redis.set(_TAVILY_BUDGET_KEY, monthly_limit)


async def initialize_tavily_budget(redis: Any, monthly_limit: int) -> None:
    """Initialize Tavily budget without replenishing it on worker restart."""
    await redis.set(_TAVILY_BUDGET_KEY, monthly_limit, nx=True)


# ---------------------------------------------------------------------------
# Agent (LLM) budget counter
# ---------------------------------------------------------------------------

_AGENT_BUDGET_KEY = "vcbrain:budget:agent"


async def get_agent_budget_remaining(redis: Any) -> int:
    """Return remaining LLM agent calls for the current month."""
    val = await redis.get(_AGENT_BUDGET_KEY)
    return int(val) if val else 0


async def decrement_agent_budget(redis: Any, amount: int = 1) -> int:
    """Decrement the agent budget counter and return the new value."""
    result: int = await redis.decrby(_AGENT_BUDGET_KEY, amount)
    return result


async def reset_agent_budget(redis: Any, monthly_limit: int) -> None:
    """Set the agent budget counter (called on worker startup)."""
    await redis.set(_AGENT_BUDGET_KEY, monthly_limit)


async def initialize_agent_budget(redis: Any, monthly_limit: int) -> None:
    """Initialize the agent budget only when the key does not exist.

    Unlike reset_agent_budget, this is safe on worker restarts and does not
    silently replenish spend capacity.
    """
    await redis.set(_AGENT_BUDGET_KEY, monthly_limit, nx=True)


# ---------------------------------------------------------------------------
# Discovery page tracker
# ---------------------------------------------------------------------------


async def get_discovery_page(redis: Any, source: str, query: str) -> int:
    """Reserve the next page number for a discovery query atomically.

    Returns a unique page reservation among concurrent callers and wraps to 1
    after page 10 to avoid going too deep.  WATCH/MULTI keeps the increment
    and wraparound in one compare-and-set transaction, so concurrent workers
    cannot both reserve page 1 at the boundary.
    """
    key = f"{_PAGE_PREFIX}{source}:{query}"
    for _attempt in range(3):
        pipe = redis.pipeline()
        try:
            await pipe.watch(key)
            current_raw = await pipe.get(key)
            try:
                current = int(current_raw) if current_raw is not None else 0
            except (TypeError, ValueError):
                current = 0
            page = current + 1
            if page > _MAX_DISCOVERY_PAGE:
                page = 1
            pipe.multi()
            pipe.set(key, page)
            await pipe.execute()
            return page
        except WatchError:
            continue
        finally:
            await pipe.reset()
    raise RuntimeError("discovery page reservation conflicted repeatedly")


async def rollback_discovery_page(redis: Any, source: str, query: str, page: int) -> None:
    """Return a failed discovery page to the tracker for a later retry.

    The tracker is intentionally advanced before the provider call so
    concurrent workers still reserve distinct pages.  A failed provider call
    can safely roll back only when the tracker still points at the failed
    reservation; a later successful reservation is never moved backwards.
    """
    key = f"{_PAGE_PREFIX}{source}:{query}"
    for _attempt in range(3):
        pipe = redis.pipeline()
        try:
            await pipe.watch(key)
            current_raw = await pipe.get(key)
            try:
                current = int(current_raw) if current_raw is not None else 0
            except (TypeError, ValueError):
                return
            if current != page:
                return
            pipe.multi()
            pipe.set(key, max(0, page - 1))
            await pipe.execute()
            return
        except WatchError:
            continue
        finally:
            await pipe.reset()


async def reset_discovery_page(redis: Any, source: str, query: str) -> None:
    """Reset the page counter for a discovery query back to 1."""
    key = f"{_PAGE_PREFIX}{source}:{query}"
    await redis.set(key, 0)
