"""Hacker News connector — discovers founders via Algolia HN API.

Free, no API key required.  Rate limit is generous (~100 req/min).

Discovery: search submissions and comments by topic, return author seeds.
Collect: fetch author's recent submissions and top comments.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from app.collectors.base import (
    Collected,
    Connector,
    ConnectorError,
    Depth,
    Seed,
    canonical_json_bytes,
)

logger = structlog.get_logger(__name__)

_ALGOLIA_API = "https://hn.algolia.com/api/v1"
_DEFAULT_HITS = 30


class HackerNewsConnector(Connector):
    name = "hackernews"
    source_type = "hackernews"
    authority = 0.4
    cost = 1.0

    async def _client(self) -> httpx.AsyncClient:
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        return httpx.AsyncClient(limits=limits, timeout=15.0)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def discover(self, query: str, page: int = 1) -> list[Seed]:
        """Search HN submissions and comments by topic, return author seeds.

        Uses Algolia's search API.  Returns authors of top stories and
        commenters on those stories.

        Args:
            query: Search topic.
            page: Page number (1-indexed, 30 results per page).
        """
        seeds: list[Seed] = []
        seen_authors: set[str] = set()

        async with await self._client() as client:
            # 1. Search stories
            params: dict[str, str | int] = {
                "query": query,
                "tags": "story",
                "hitsPerPage": _DEFAULT_HITS,
                "page": page - 1,  # Algolia is 0-indexed
            }
            resp = await client.get(f"{_ALGOLIA_API}/search", params=params)
            if resp.status_code == 429:
                raise ConnectorError("hackernews_rate_limited: HTTP 429")
            if resp.status_code != 200:
                logger.error("hn_search_failed", status=resp.status_code)
                return []

            data = resp.json()
            for hit in data.get("hits", []):
                author = hit.get("author", "")
                if author and author.lower() not in seen_authors:
                    seen_authors.add(author.lower())
                    seeds.append(
                        Seed(
                            source_type="hackernews",
                            handle=author,
                            display_hint=author,
                            metadata={
                                "query": query,
                                "story_title": hit.get("title", ""),
                                "points": hit.get("points", 0),
                            },
                        )
                    )

            # 2. Search comments for the same query to find active commenters
            params["tags"] = "comment"
            resp = await client.get(f"{_ALGOLIA_API}/search", params=params)
            if resp.status_code == 429:
                raise ConnectorError("hackernews_rate_limited: HTTP 429")
            if resp.status_code == 200:
                data = resp.json()
                for hit in data.get("hits", []):
                    author = hit.get("author", "")
                    if author and author.lower() not in seen_authors:
                        seen_authors.add(author.lower())
                        seeds.append(
                            Seed(
                                source_type="hackernews",
                                handle=author,
                                display_hint=author,
                                metadata={
                                    "query": query,
                                    "comment_mention": hit.get("story_title", ""),
                                },
                            )
                        )

        return seeds

    # ------------------------------------------------------------------
    # Collect
    # ------------------------------------------------------------------

    async def collect(self, seed: Seed, depth: Depth = "light") -> Collected:
        username = seed.handle
        observations: list[dict[str, object]] = []
        now = datetime.now(UTC)

        async with await self._client() as client:
            # Fetch user profile
            user_resp = await client.get(f"{_ALGOLIA_API}/users/{username}")
            if user_resp.status_code != 200:
                raise ConnectorError(f"hn_user_fetch_failed: {user_resp.status_code}")
            user_data: dict[str, Any] = user_resp.json()

            observations.append(
                {
                    "predicate": "hn_username",
                    "object_value": username,
                    "observed_at": now.isoformat(),
                    "confidence": 1.0,
                }
            )
            karma = user_data.get("karma", 0)
            observations.append(
                {
                    "predicate": "hn_karma",
                    "object_value": str(karma),
                    "observed_at": now.isoformat(),
                    "confidence": 1.0,
                }
            )
            about = user_data.get("about", "")
            if about:
                observations.append(
                    {
                        "predicate": "hn_about",
                        "object_value": about[:2000],
                        "observed_at": now.isoformat(),
                        "confidence": 0.8,
                    }
                )

            # Fetch recent submissions
            limit = 50 if depth == "deep" else 20
            stories_resp = await client.get(
                f"{_ALGOLIA_API}/search",
                params={
                    "query": "",
                    "tags": f"story,author_{username}",
                    "hitsPerPage": limit,
                },
            )
            stories: list[dict[str, Any]] = []
            if stories_resp.status_code == 200:
                stories = stories_resp.json().get("hits", [])

            story_count = len(stories)
            total_points = sum(s.get("points", 0) for s in stories)
            story_titles = [s.get("title", "") for s in stories if s.get("title")]

            observations.append(
                {
                    "predicate": "hn_story_count",
                    "object_value": str(story_count),
                    "observed_at": now.isoformat(),
                    "confidence": 1.0,
                }
            )
            observations.append(
                {
                    "predicate": "hn_total_points",
                    "object_value": str(total_points),
                    "observed_at": now.isoformat(),
                    "confidence": 1.0,
                }
            )
            if story_titles:
                observations.append(
                    {
                        "predicate": "hn_recent_stories",
                        "object_value": " | ".join(story_titles[:10]),
                        "observed_at": now.isoformat(),
                        "confidence": 0.9,
                    }
                )

            # Deep: fetch top comments
            if depth == "deep":
                comments_resp = await client.get(
                    f"{_ALGOLIA_API}/search",
                    params={
                        "query": "",
                        "tags": f"comment,author_{username}",
                        "hitsPerPage": 30,
                    },
                )
                if comments_resp.status_code == 200:
                    comments = comments_resp.json().get("hits", [])
                    comment_texts = [
                        c.get("comment_text", "")[:500] for c in comments if c.get("comment_text")
                    ]
                    if comment_texts:
                        observations.append(
                            {
                                "predicate": "hn_recent_comments",
                                "object_value": " | ".join(comment_texts[:10]),
                                "observed_at": now.isoformat(),
                                "confidence": 0.7,
                            }
                        )

        raw_bytes = canonical_json_bytes({"user": user_data, "stories": stories})
        return Collected(
            content=raw_bytes,
            content_type="application/json",
            observations=observations,
            source_type="hackernews",
            uri=f"https://news.ycombinator.com/user?id={username}",
            license_hint={
                "source": "Algolia HN API",
                "terms": "https://hn.algolia.com/api",
            },
        )
