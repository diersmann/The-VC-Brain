"""Hackathons connector — discovers founders via Tavily search.

Tavily searches for Devpost and MLH public project pages.
Those URLs are collected via the generic 'web' connector.

No official API exists for Devpost or MLH.  This is inherently brittle
and may break if those sites change their structure.

Discovery: Tavily search for "devpost <query>" or "mlh <query>".
Collect: delegates to the 'web' connector for the project URL.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog
from tavily import TavilyClient  # type: ignore[import-untyped]

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

_HACKATHON_DOMAINS = {"devpost.com", "mlh.io"}


class HackathonsConnector(Connector):
    name = "hackathons"
    source_type = "hackathons"
    authority = 0.5
    cost = 2.0

    def __init__(self) -> None:
        self._tavily: TavilyClient | None = None

    def _get_tavily(self) -> TavilyClient | None:
        if self._tavily is not None:
            return self._tavily
        from app.config import get_settings

        settings = get_settings()
        if settings.tavily_api_key:
            self._tavily = TavilyClient(api_key=settings.tavily_api_key)
            return self._tavily
        return None

    async def discover(self, query: str, page: int = 1) -> list[Seed]:
        """Search Tavily for hackathon project pages.

        Searches both devpost.com and mlh.io for the given topic.

        Note: Tavily basic search does not support pagination.
        The page parameter is accepted for interface consistency.
        """
        tavily = self._get_tavily()
        if not tavily:
            logger.warning("hackathons_discover_skipped_no_tavily_key")
            return []

        seeds: list[Seed] = []
        seen_urls: set[str] = set()

        for domain in _HACKATHON_DOMAINS:
            search_query = f"site:{domain} {query}"
            try:
                response = await asyncio.to_thread(
                    tavily.search,
                    query=search_query,
                    search_depth="basic",
                    max_results=10,
                    include_answer=False,
                    include_raw_content=False,
                )
            except Exception as exc:
                logger.warning("tavily_search_failed", query=search_query, error=str(exc))
                if classify_connector_failure(exc)[0] == "rate_limited":
                    raise ConnectorError(f"hackathons_search_rate_limited: {exc}") from exc
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
                        source_type="hackathons",
                        handle=url,
                        display_hint=title or url,
                        metadata={
                            "query": query,
                            "domain": domain,
                            "title": title,
                            "snippet": content[:500] if content else "",
                        },
                    )
                )

        return seeds

    async def collect(self, seed: Seed, depth: Depth = "light") -> Collected:
        """Collect a hackathon project page via the generic web connector."""
        web_connector = get_connector("web")
        try:
            collected = await web_connector.collect(seed, depth=depth)
        except Exception as exc:
            raise ConnectorError(f"hackathons_collect_via_web_failed: {exc}") from exc

        now = datetime.now(UTC)
        tagged_observations: list[dict[str, object]] = [
            {
                "predicate": "hackathon_url",
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
            source_type="hackathons",
            uri=seed.handle,
            license_hint={
                "source": "Tavily Search + Extract",
                "terms": "https://tavily.com",
                "note": "No official API; relies on Tavily crawling public pages",
            },
        )
