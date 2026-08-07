"""Podcasts connector — discovers founder podcast appearances via Tavily search.

Tavily searches for podcast episodes featuring the query topic.
Episode URLs are collected via the generic 'web' connector.

No transcription in MVP (that's Phase 3 — would need Whisper or a
transcript API like Listen Notes or Podchaser).

Discovery: Tavily search for "podcast <query> founder/CEO".
Collect: delegates to the 'web' connector for the episode URL.
"""

from __future__ import annotations

import asyncio
import inspect
from datetime import UTC, datetime

import structlog
from tavily import TavilyClient  # type: ignore[import-untyped]

from app.client_lifecycle import get_tavily_client
from app.collectors.base import (
    Collected,
    Connector,
    ConnectorError,
    Depth,
    Seed,
    classify_connector_failure,
)
from app.collectors.registry import get_connector

logger = structlog.get_logger(__name__)

_PODCAST_KEYWORDS = [
    "podcast",
    "episode",
    "interview",
    "talks at",
    "founder story",
]


class PodcastsConnector(Connector):
    name = "podcasts"
    source_type = "podcasts"
    authority = 0.4
    cost = 4.0

    async def _get_tavily(self) -> TavilyClient | None:
        from app.config import get_settings

        settings = get_settings()
        if settings.tavily_api_key:
            return await get_tavily_client(
                settings.tavily_api_key,
                factory=TavilyClient,
            )
        return None

    async def discover(self, query: str, page: int = 1) -> list[Seed]:
        """Search Tavily for podcast episodes matching the query.

        Constructs searches like "podcast <query> founder" to find
        podcast episode URLs.

        Note: Tavily basic search does not support pagination.
        The page parameter is accepted for interface consistency.
        """
        maybe_tavily = self._get_tavily()
        tavily = await maybe_tavily if inspect.isawaitable(maybe_tavily) else maybe_tavily
        if not tavily:
            logger.warning("podcasts_discover_skipped_no_tavily_key")
            return []

        seeds: list[Seed] = []
        seen_urls: set[str] = set()

        for keyword in _PODCAST_KEYWORDS:
            search_query = f"{keyword} {query} founder"
            try:
                response = await asyncio.to_thread(
                    tavily.search,
                    query=search_query,
                    search_depth="basic",
                    max_results=5,
                    include_answer=False,
                    include_raw_content=False,
                )
            except Exception as exc:
                logger.warning("tavily_search_failed", query=search_query, error=str(exc))
                if classify_connector_failure(exc)[0] == "rate_limited":
                    raise ConnectorError(f"podcasts_search_rate_limited: {exc}") from exc
                continue

            results = response.get("results", [])
            for result in results:
                url = result.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                title = result.get("title", "")
                content = result.get("content", "")

                seeds.append(
                    Seed(
                        source_type="podcasts",
                        handle=url,
                        display_hint=title or url,
                        metadata={
                            "query": query,
                            "keyword": keyword,
                            "title": title,
                            "snippet": content[:500] if content else "",
                        },
                    )
                )

        return seeds

    async def collect(self, seed: Seed, depth: Depth = "light") -> Collected:
        """Collect a podcast episode page via the generic web connector."""
        web_connector = get_connector("web")
        try:
            collected = await web_connector.collect(seed, depth=depth)
        except Exception as exc:
            raise ConnectorError(f"podcasts_collect_via_web_failed: {exc}") from exc

        now = datetime.now(UTC)
        tagged_observations: list[dict[str, object]] = [
            {
                "predicate": "podcast_url",
                "object_value": seed.handle,
                "observed_at": now.isoformat(),
                "confidence": 1.0,
            }
        ]
        tagged_observations.extend(collected.observations)

        return Collected(
            content=collected.content,
            content_type=collected.content_type,
            observations=tagged_observations,
            source_type="podcasts",
            uri=seed.handle,
            license_hint={
                "source": "Tavily Search + Extract",
                "terms": "https://tavily.com",
                "note": "No transcription in MVP",
            },
        )
