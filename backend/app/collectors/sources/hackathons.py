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
    normalize_connector_error,
)
from app.collectors.registry import get_connector

logger = structlog.get_logger(__name__)

_HACKATHON_DOMAINS = {"devpost.com", "mlh.io"}


class HackathonsConnector(Connector):
    name = "hackathons"
    source_type = "hackathons"
    authority = 0.5
    cost = 2.0

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
        """Search Tavily for hackathon project pages.

        Searches both devpost.com and mlh.io for the given topic.

        Note: Tavily basic search does not support pagination.
        The page parameter is accepted for interface consistency.
        """
        try:
            maybe_tavily = self._get_tavily()
            tavily = await maybe_tavily if inspect.isawaitable(maybe_tavily) else maybe_tavily
        except Exception as exc:
            raise normalize_connector_error(exc, context="hackathons_search_failed") from exc
        if not tavily:
            logger.warning("hackathons_discover_skipped_no_tavily_key")
            raise ConnectorError("hackathons_search_not_configured")

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
                if isinstance(exc, ConnectorError):
                    raise
                raise normalize_connector_error(exc, context="hackathons_search_failed") from exc

            try:
                results = response.get("results", [])
                if (
                    not isinstance(response, dict)
                    or "results" not in response
                    or not isinstance(results, list)
                ):
                    raise TypeError("missing results")
            except Exception as exc:
                raise normalize_connector_error(
                    exc, context="hackathons_search_failed: invalid provider response"
                ) from exc
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
