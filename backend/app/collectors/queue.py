"""Redis-backed priority queue for collection tasks.

Uses three sorted sets (high / normal / low) so the dispatcher can
respect priority lanes.  Score = negative priority (lower = first).
"""

from __future__ import annotations

import json
from typing import Any

import structlog

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
    tasks: list[dict[str, Any]] = []
    for lane in ("high", "normal", "low"):
        if len(tasks) >= n:
            break
        key = _QUEUE_KEYS[lane]
        # Pop the lowest score (highest priority) member
        results = await redis.zpopmin(key, count=n - len(tasks))
        for member, _score in results:
            tasks.append(json.loads(member))
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
    """Get the next page number for a discovery query, auto-incrementing.

    Returns the current page and advances the counter so the next call
    gets the next page.  Resets to 1 after page 10 to avoid going too deep.
    """
    key = f"{_PAGE_PREFIX}{source}:{query}"
    page = await redis.incr(key)
    if page > 10:
        await redis.set(key, 1)
        page = 1
    return page  # type: ignore[no-any-return]


async def reset_discovery_page(redis: Any, source: str, query: str) -> None:
    """Reset the page counter for a discovery query back to 1."""
    key = f"{_PAGE_PREFIX}{source}:{query}"
    await redis.set(key, 0)
