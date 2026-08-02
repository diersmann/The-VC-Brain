"""Product Hunt connector — discovers and collects maker/product data.

Lightweight: post metadata + makers.
Deep: maker's other posts + comments.
"""

from __future__ import annotations

from datetime import UTC, datetime

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

_API_BASE = "https://api.producthunt.com/v2/api/graphql"
_DEFAULT_PER_PAGE = 20


class ProductHuntConnector(Connector):
    name = "producthunt"
    source_type = "producthunt"
    authority = 0.7
    cost = 1.5

    def __init__(self) -> None:
        self._token: str | None = None

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json", "User-Agent": "The-VC-Brain/0.1"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def _client(self) -> httpx.AsyncClient:
        from app.config import get_settings

        settings = get_settings()
        self._token = settings.producthunt_token or None
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        return httpx.AsyncClient(headers=self._headers(), limits=limits, timeout=15.0)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def discover(self, query: str, page: int = 1) -> list[Seed]:
        """Search Product Hunt posts by topic, return maker seeds.

        Args:
            query: Search topic.
            page: Page number (1-indexed, 20 results per page).
        """
        graphql_query = """
        query SearchPosts($query: String!, $first: Int!, $after: String) {
            posts(order: VOTES, first: $first, after: $after) {
                edges {
                    node {
                        id
                        name
                        tagline
                        url
                        votesCount
                        makers {
                            id
                            username
                            name
                        }
                    }
                }
            }
        }
        """
        # For MVP, we use page as a simple offset via cursor
        after = str((page - 1) * _DEFAULT_PER_PAGE) if page > 1 else None
        payload = {
            "query": graphql_query,
            "variables": {"query": query, "first": _DEFAULT_PER_PAGE, "after": after},
        }

        async with await self._client() as client:
            resp = await client.post(_API_BASE, json=payload)

        if resp.status_code != 200:
            logger.error("producthunt_search_failed", status=resp.status_code)
            return []

        data = resp.json()
        seeds: list[Seed] = []
        posts = data.get("data", {}).get("posts", {}).get("edges", [])
        for edge in posts:
            post = edge.get("node", {})
            makers = post.get("makers", [])
            for maker in makers:
                username = maker.get("username", "")
                if username:
                    seeds.append(
                        Seed(
                            source_type="producthunt",
                            handle=username,
                            display_hint=maker.get("name", username),
                            metadata={"ph_post_id": post.get("id"), "query": query},
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

        graphql_query = """
        query UserPosts($username: String!, $first: Int!) {
            user(username: $username) {
                id
                name
                username
                profileImage
                headline
                websiteUrl
                twitterUsername
                posts(first: $first) {
                    edges {
                        node {
                            id
                            name
                            tagline
                            url
                            votesCount
                            commentsCount
                            createdAt
                        }
                    }
                }
            }
        }
        """
        first = 50 if depth == "deep" else 20
        payload = {
            "query": graphql_query,
            "variables": {"username": username, "first": first},
        }

        async with await self._client() as client:
            resp = await client.post(_API_BASE, json=payload)

        if resp.status_code != 200:
            raise ConnectorError(f"producthunt_user_fetch_failed: {resp.status_code}")

        data = resp.json()
        user = data.get("data", {}).get("user")
        if not user:
            raise ConnectorError(f"producthunt_user_not_found: {username}")

        observations.append(
            {
                "predicate": "producthunt_username",
                "object_value": username,
                "observed_at": now.isoformat(),
                "confidence": 1.0,
            }
        )
        if user.get("name"):
            observations.append(
                {
                    "predicate": "display_name",
                    "object_value": user["name"],
                    "observed_at": now.isoformat(),
                    "confidence": 0.9,
                }
            )
        if user.get("headline"):
            observations.append(
                {
                    "predicate": "headline",
                    "object_value": user["headline"],
                    "observed_at": now.isoformat(),
                    "confidence": 0.8,
                }
            )
        if user.get("websiteUrl"):
            observations.append(
                {
                    "predicate": "website_url",
                    "object_value": user["websiteUrl"],
                    "observed_at": now.isoformat(),
                    "confidence": 0.9,
                }
            )
        if user.get("twitterUsername"):
            observations.append(
                {
                    "predicate": "twitter_handle",
                    "object_value": user["twitterUsername"],
                    "observed_at": now.isoformat(),
                    "confidence": 0.9,
                }
            )

        posts = user.get("posts", {}).get("edges", [])
        total_upvotes = 0
        for edge in posts:
            post = edge.get("node", {})
            total_upvotes += post.get("votesCount", 0)

        observations.append(
            {
                "predicate": "producthunt_posts",
                "object_value": str(len(posts)),
                "observed_at": now.isoformat(),
                "confidence": 1.0,
            }
        )
        observations.append(
            {
                "predicate": "producthunt_total_upvotes",
                "object_value": str(total_upvotes),
                "observed_at": now.isoformat(),
                "confidence": 1.0,
            }
        )

        raw_bytes = canonical_json_bytes(data)
        return Collected(
            content=raw_bytes,
            content_type="application/json",
            observations=observations,
            source_type="producthunt",
            uri=f"https://www.producthunt.com/@{username}",
            license_hint={"source": "Product Hunt API", "terms": "https://api.producthunt.com/v2/docs"},
        )
