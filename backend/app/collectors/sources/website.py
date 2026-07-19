"""Generic website connector — fetches and extracts content from arbitrary URLs.

Uses Tavily Extract as the primary fetcher (returns clean markdown + citations).
Falls back to raw HTTP GET + HTML if Tavily is unavailable.

Observations: title, meta description, H1s, outbound links to known source domains.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import structlog
from tavily import TavilyClient  # type: ignore[import-untyped]

from app.collectors.base import Collected, Connector, ConnectorError, Depth, Seed

logger = structlog.get_logger(__name__)

# Domains that trigger cross-source seed creation
_KNOWN_SOURCE_DOMAINS = {
    "github.com",
    "producthunt.com",
    "arxiv.org",
    "linkedin.com",
    "youtube.com",
    "devpost.com",
    "mlh.io",
    "hackernews.com",
    "news.ycombinator.com",
}


class WebsiteConnector(Connector):
    name = "web"
    source_type = "web"
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
        """Website connector does not do discovery — use TavilySearchConnector."""
        return []

    async def collect(self, seed: Seed, depth: Depth = "light") -> Collected:
        url = seed.handle
        observations: list[dict[str, object]] = []
        now = datetime.now(UTC)

        content: bytes
        content_type: str

        # Try Tavily Extract first
        tavily = self._get_tavily()
        if tavily:
            try:
                result = tavily.extract(url=url, extract_depth="basic")
                if result and result.get("results"):
                    page = result["results"][0]
                    raw_text = page.get("raw_content", "")
                    if raw_text:
                        content = raw_text.encode("utf-8")
                        content_type = "text/markdown"

                        observations.append(
                            {
                                "predicate": "page_title",
                                "object_value": page.get("title", ""),
                                "observed_at": now.isoformat(),
                                "confidence": 0.9,
                            }
                        )
                        observations.append(
                            {
                                "predicate": "page_content",
                                "object_value": raw_text[:5000],
                                "observed_at": now.isoformat(),
                                "confidence": 0.7,
                            }
                        )

                        # Extract outbound links to known source domains
                        links = self._extract_known_links(raw_text)
                        for link in links:
                            observations.append(
                                {
                                    "predicate": "outbound_link",
                                    "object_value": link,
                                    "observed_at": now.isoformat(),
                                    "confidence": 0.8,
                                }
                            )

                        return Collected(
                            content=content,
                            content_type=content_type,
                            observations=observations,
                            source_type="web",
                            uri=url,
                            license_hint={"source": "Tavily Extract", "terms": "https://tavily.com"},
                        )
            except Exception as exc:
                logger.warning("tavily_extract_failed", url=url, error=str(exc))

        # Fallback: raw HTTP GET
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                resp = await client.get(url, headers={"User-Agent": "The-VC-Brain/0.1"})
                resp.raise_for_status()
                content = resp.content
                content_type = resp.headers.get("content-type", "text/html") or "text/html"

                observations.append(
                    {
                        "predicate": "page_title",
                        "object_value": url,
                        "observed_at": now.isoformat(),
                        "confidence": 0.5,
                    }
                )
                observations.append(
                    {
                        "predicate": "http_status",
                        "object_value": str(resp.status_code),
                        "observed_at": now.isoformat(),
                        "confidence": 1.0,
                    }
                )
            except httpx.HTTPError as exc:
                raise ConnectorError(f"website_fetch_failed: {exc}") from exc

        return Collected(
            content=content,
            content_type=content_type,
            observations=observations,
            source_type="web",
            uri=url,
        )

    def _extract_known_links(self, text: str) -> list[str]:
        """Extract URLs pointing to known source domains from text."""
        import re

        links: list[str] = []
        url_pattern = re.compile(r"https?://([^/\s]+)([^\s]*)")
        for match in url_pattern.finditer(text):
            domain = match.group(1).lower()
            for known in _KNOWN_SOURCE_DOMAINS:
                if domain == known or domain.endswith("." + known):
                    links.append(match.group(0))
                    break
        return links
