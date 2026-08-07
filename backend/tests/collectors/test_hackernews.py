"""Tests for the Hacker News connector.

Uses respx to mock httpx calls to the Algolia HN API.
"""

from __future__ import annotations

import pytest
import respx

from app.collectors.base import ConnectorError, Seed
from app.collectors.sources.hackernews import HackerNewsConnector


@pytest.fixture
def connector() -> HackerNewsConnector:
    return HackerNewsConnector()


def make_seed(username: str) -> Seed:
    return Seed(source_type="hackernews", handle=username, display_hint=username)


@pytest.mark.asyncio
async def test_discover_returns_seeds(connector: HackerNewsConnector) -> None:
    """Discover should return Seed objects from search results."""
    with respx.mock:
        # Stories search
        respx.get("https://hn.algolia.com/api/v1/search").respond(
            json={
                "hits": [
                    {"author": "user1", "title": "My AI Project", "points": 50},
                    {"author": "user2", "title": "ML in Production", "points": 120},
                ]
            }
        )

        seeds = await connector.discover("machine learning")
        assert len(seeds) >= 2
        handles = {s.handle for s in seeds}
        assert "user1" in handles
        assert "user2" in handles


@pytest.mark.asyncio
async def test_discover_handles_api_error(connector: HackerNewsConnector) -> None:
    """API errors must not be recorded as a successful empty page."""
    with respx.mock:
        respx.get("https://hn.algolia.com/api/v1/search").respond(status_code=500)

        with pytest.raises(ConnectorError, match="HTTP 500"):
            await connector.discover("machine learning")


@pytest.mark.asyncio
async def test_collect_light_returns_collected(connector: HackerNewsConnector) -> None:
    """Light collect should return a Collected with observations."""
    username = "testuser"
    with respx.mock:
        # User profile
        respx.get(f"https://hn.algolia.com/api/v1/users/{username}").respond(
            json={
                "username": username,
                "karma": 500,
                "about": "ML engineer and open source contributor.",
            }
        )
        # Stories
        respx.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": "", "tags": f"story,author_{username}", "hitsPerPage": 20},
        ).respond(
            json={
                "hits": [
                    {"title": "My HN Post", "points": 100},
                    {"title": "Another Post", "points": 50},
                ]
            }
        )

        seed = make_seed(username)
        collected = await connector.collect(seed, depth="light")

        assert collected.source_type == "hackernews"
        assert collected.uri == f"https://news.ycombinator.com/user?id={username}"
        assert len(collected.observations) > 0

        obs: dict[str, str] = {}
        for o in collected.observations:
            pred = str(o.get("predicate", ""))
            val = str(o.get("object_value", ""))
            obs[pred] = val

        assert obs["hn_username"] == username
        assert obs["hn_karma"] == "500"
        assert obs["hn_story_count"] == "2"
        assert obs["hn_total_points"] == "150"


@pytest.mark.asyncio
async def test_collect_deep_includes_comments(connector: HackerNewsConnector) -> None:
    """Deep collect should include recent comments."""
    username = "testuser"
    with respx.mock:
        # User profile
        respx.get(f"https://hn.algolia.com/api/v1/users/{username}").respond(
            json={"username": username, "karma": 100}
        )
        # Stories (deep: 50 per page)
        respx.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": "", "tags": f"story,author_{username}", "hitsPerPage": 50},
        ).respond(json={"hits": [{"title": "My Post", "points": 30}]})
        # Comments
        respx.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": "", "tags": f"comment,author_{username}", "hitsPerPage": 30},
        ).respond(
            json={
                "hits": [
                    {"comment_text": "Great project! I built something similar."},
                    {"comment_text": "Have you tried using PyTorch instead?"},
                ]
            }
        )

        seed = make_seed(username)
        collected = await connector.collect(seed, depth="deep")

        obs: dict[str, str] = {}
        for o in collected.observations:
            pred = str(o.get("predicate", ""))
            val = str(o.get("object_value", ""))
            obs[pred] = val

        assert "hn_recent_comments" in obs
        assert "Great project" in obs["hn_recent_comments"]
