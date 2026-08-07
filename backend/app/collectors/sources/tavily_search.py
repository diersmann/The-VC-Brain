"""Tavily Search connector — discovers candidate URLs and named entities.

This is the discovery entrypoint for the open web.  Given a thesis query,
Tavily returns search results with URLs, titles, and named entities.
These become seeds for the generic website connector (and potentially
for LinkedIn, hackathons, YouTube, podcasts, etc.).
"""

from __future__ import annotations

import asyncio
import inspect

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

logger = structlog.get_logger(__name__)


class TavilySearchConnector(Connector):
    name = "tavily_search"
    source_type = "tavily_search"
    authority = 0.6
    cost = 2.0

    async def _get_client(self) -> TavilyClient:
        from app.config import get_settings

        settings = get_settings()
        if not settings.tavily_api_key:
            logger.warning("tavily_api_key_not_configured")
            raise ConnectorError("tavily_search_not_configured")
        return await get_tavily_client(
            settings.tavily_api_key,
            factory=TavilyClient,
        )

    async def discover(self, query: str, page: int = 1) -> list[Seed]:
        """Search Tavily and return seeds from results.

        Each result becomes a Seed with source_type="web".
        Named entities (persons, organizations) are extracted from the
        result snippet using a simple heuristic (proper NER is Phase 2).

        Note: Tavily basic search does not support pagination.
        The page parameter is accepted for interface consistency.
        """
        try:
            maybe_client = self._get_client()
            client = await maybe_client if inspect.isawaitable(maybe_client) else maybe_client
            if client is None:
                raise ConnectorError("tavily_search_not_configured")
            response = await asyncio.to_thread(
                client.search,
                query=query,
                search_depth="basic",
                max_results=10,
                include_answer=False,
                include_raw_content=False,
            )
        except Exception as exc:
            logger.error("tavily_search_failed", query=query, error=str(exc))
            if isinstance(exc, ConnectorError):
                raise
            raise normalize_connector_error(exc, context="tavily_search_failed") from exc

        seeds: list[Seed] = []
        seen_urls: set[str] = set()

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
                exc, context="tavily_search_failed: invalid provider response"
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
                    source_type="web",
                    handle=url,
                    display_hint=title or url,
                    metadata={
                        "query": query,
                        "title": title,
                        "snippet": content[:500] if content else "",
                    },
                )
            )

            # Extract named entities from content (simple heuristic)
            # Phase 2: replace with proper NER / LLM extraction
            entities = self._extract_entities(title, content)
            for entity_name, entity_type in entities:
                if entity_type == "person":
                    seeds.append(
                        Seed(
                            source_type="tavily_entity",
                            handle=entity_name,
                            display_hint=entity_name,
                            metadata={"query": query, "entity_type": "person"},
                        )
                    )

        return seeds

    def _extract_entities(self, title: str, content: str) -> list[tuple[str, str]]:
        """Simple heuristic entity extraction from text.

        Returns list of (name, type) tuples.
        Types: "person", "organization".
        """
        entities: list[tuple[str, str]] = []
        text = f"{title}. {content}"

        # Very simple: look for "CEO", "founder", "co-founder" patterns
        import re

        patterns = [
            (r"([A-Z][a-z]+ [A-Z][a-z]+),?\s+(CEO|founder|co-founder|CTO|COO)", "person"),
            (r"(founder|co-founder|CEO)\s+of\s+([A-Z][A-Za-z0-9]+)", "person"),
        ]

        for pattern, entity_type in patterns:
            for match in re.finditer(pattern, text):
                # Extract the name part (first capture group)
                groups = match.groups()
                name = groups[0] if len(groups) >= 1 else ""
                if name and len(name.split()) >= 2:
                    entities.append((name, entity_type))

        return entities

    async def collect(self, seed: Seed, depth: Depth = "light") -> Collected:
        """Tavily Search is discovery-only. Use the 'web' connector for collection."""
        raise NotImplementedError(
            "tavily_search is discovery-only; use 'web' connector for collection"
        )
