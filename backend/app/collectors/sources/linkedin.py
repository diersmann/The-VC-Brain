"""LinkedIn connector — discovers founders via Tavily search.

Legal posture: Tavily search only, never direct fetch.
Tavily may surface public LinkedIn profile URLs in its search results.
Those URLs are collected via the generic 'web' connector (Tavily Extract),
which returns the public-facing content that Tavily can access.

Discovery: Tavily search for "linkedin <query> founder/CEO".
Collect: delegates to the 'web' connector for the profile URL.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog
from tavily import TavilyClient  # type: ignore[import-untyped]

from app.collectors.base import Collected, Connector, ConnectorError, Depth, Seed
from app.collectors.registry import get_connector

logger = structlog.get_logger(__name__)


class LinkedInConnector(Connector):
    name = "linkedin"
    source_type = "linkedin"
    authority = 0.6
    cost = 5.0

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
        """Search Tavily for LinkedIn profiles matching the query.

        Constructs a search like "linkedin <query> founder" to find
        public LinkedIn profile URLs.

        Note: Tavily basic search does not support pagination.
        The page parameter is accepted for interface consistency.
        """
        tavily = self._get_tavily()
        if not tavily:
            logger.warning("linkedin_discover_skipped_no_tavily_key")
            return []

        search_query = f"linkedin {query} founder"
        seeds: list[Seed] = []

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
            logger.error("tavily_search_failed", query=search_query, error=str(exc))
            return []

        results = response.get("results", [])
        for result in results:
            url = result.get("url", "")
            if not url or "linkedin.com/in/" not in url.lower():
                continue

            title = result.get("title", "")
            content = result.get("content", "")

            # Extract the profile name from the URL or title
            profile_name = title.replace(" - LinkedIn", "").replace(" | LinkedIn", "").strip()
            if not profile_name:
                # Fallback: extract from URL path
                path_parts = url.split("/in/")[-1].split("/")[0]
                profile_name = path_parts.replace("-", " ").title()

            seeds.append(
                Seed(
                    source_type="linkedin",
                    handle=url,
                    display_hint=profile_name or url,
                    metadata={
                        "query": query,
                        "title": title,
                        "snippet": content[:500] if content else "",
                    },
                )
            )

        return seeds

    async def collect(self, seed: Seed, depth: Depth = "light") -> Collected:
        """Collect a LinkedIn profile via the generic web connector.

        Delegates to the 'web' connector which uses Tavily Extract.
        Never fetches linkedin.com directly.
        """
        web_connector = get_connector("web")
        try:
            collected = await web_connector.collect(seed, depth=depth)
        except Exception as exc:
            raise ConnectorError(f"linkedin_collect_via_web_failed: {exc}") from exc

        # Tag observations with linkedin source type
        now = datetime.now(UTC)
        tagged_observations: list[dict[str, object]] = [
            {
                "predicate": "linkedin_url",
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
            source_type="linkedin",
            uri=seed.handle,
            license_hint={
                "source": "Tavily Search + Extract",
                "terms": "https://tavily.com",
                "note": "Never fetches linkedin.com directly",
            },
        )
