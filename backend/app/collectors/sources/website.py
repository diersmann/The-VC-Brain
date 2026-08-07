"""Generic website connector — fetches and extracts content from arbitrary URLs.

Uses Tavily Extract as the primary fetcher (returns clean markdown + citations).
Falls back to raw HTTP GET + HTML if Tavily is unavailable.

Observations: title, meta description, H1s, outbound links to known source domains.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse

import httpx
import structlog
from tavily import TavilyClient  # type: ignore[import-untyped]

from app.collectors.base import Collected, Connector, ConnectorError, Depth, Seed

logger = structlog.get_logger(__name__)

_MAX_REDIRECTS = 5
_LOCAL_HOST_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home.arpa")


def _validate_http_url(raw_url: str) -> str:
    """Reject non-HTTP URLs and obvious local-network targets before fetching."""
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ConnectorError("website_url_rejected: only public http(s) URLs are allowed")
    if parsed.username or parsed.password:
        raise ConnectorError("website_url_rejected: credentials in URL are not allowed")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ConnectorError("website_url_rejected: invalid port") from exc
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(
        _LOCAL_HOST_SUFFIXES
    ):
        raise ConnectorError("website_url_rejected: local hostname is not allowed")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ConnectorError("website_url_rejected: private or reserved address")
    if port is not None and not 1 <= port <= 65535:
        raise ConnectorError("website_url_rejected: invalid port")
    return parsed.geturl()


async def _validate_resolved_host(url: str) -> None:
    """Resolve a hostname and reject private/reserved answers before connecting."""
    parsed = urlparse(url)
    hostname = parsed.hostname
    if hostname is None:
        raise ConnectorError("website_url_rejected: missing hostname")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = await asyncio.to_thread(
            socket.getaddrinfo,
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except (OSError, ValueError) as exc:
        raise ConnectorError("website_fetch_failed: hostname resolution failed") from exc
    resolved = {ipaddress.ip_address(item[4][0]) for item in addresses}
    if not resolved or any(not address.is_global for address in resolved):
        raise ConnectorError(
            "website_url_rejected: hostname resolves to private or reserved address"
        )


async def _fetch_bounded_http(url: str, max_bytes: int) -> tuple[str, bytes, str, int]:
    """Fetch with validated redirects and a streamed response-size bound."""
    current_url = _validate_http_url(url)
    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=False,
        # Do not let process-wide HTTP(S)_PROXY variables redirect connector traffic.
        trust_env=False,
    ) as client:
        for _ in range(_MAX_REDIRECTS + 1):
            await _validate_resolved_host(current_url)
            async with client.stream(
                "GET", current_url, headers={"User-Agent": "The-VC-Brain/0.1"}
            ) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise ConnectorError("website_fetch_failed: redirect has no location")
                    current_url = _validate_http_url(urljoin(current_url, location))
                    continue
                response.raise_for_status()
                content_length = response.headers.get("content-length")
                if content_length and content_length.isdigit() and int(content_length) > max_bytes:
                    raise ConnectorError("website_fetch_failed: response exceeds byte limit")
                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise ConnectorError("website_fetch_failed: response exceeds byte limit")
                    chunks.append(chunk)
                return current_url, b"".join(chunks), response.headers.get(
                    "content-type", "text/html"
                ), response.status_code
        raise ConnectorError("website_fetch_failed: too many redirects")

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
        url = _validate_http_url(seed.handle)
        # Apply the same DNS-level private/reserved-target check before handing the
        # URL to Tavily as before issuing our own raw HTTP request.
        await _validate_resolved_host(url)
        observations: list[dict[str, object]] = []
        now = datetime.now(UTC)
        from app.config import get_settings

        max_bytes = get_settings().website_max_bytes

        content: bytes
        content_type: str

        # Try Tavily Extract first
        tavily = self._get_tavily()
        if tavily:
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(tavily.extract, url=url, extract_depth="basic"),
                    timeout=15.0,
                )
                if result and result.get("results"):
                    page = result["results"][0]
                    raw_text = page.get("raw_content", "")
                    if raw_text:
                        content = raw_text.encode("utf-8")
                        if len(content) > max_bytes:
                            raise ConnectorError(
                                "website_fetch_failed: response exceeds byte limit"
                            )
                        content_type = "text/markdown"

                        raw_page_title = page.get("title")
                        page_title = (
                            raw_page_title.strip() if isinstance(raw_page_title, str) else ""
                        )
                        if page_title:
                            observations.append(
                                {
                                    "predicate": "page_title",
                                    "object_value": page_title,
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

        # Fallback: bounded raw HTTP GET with redirect validation.
        try:
            final_url, content, content_type, status_code = await _fetch_bounded_http(
                url, max_bytes
            )
        except httpx.HTTPError as exc:
            raise ConnectorError(f"website_fetch_failed: {exc}") from exc

        observations.append(
            {
                "predicate": "page_title",
                "object_value": final_url,
                "observed_at": now.isoformat(),
                "confidence": 0.5,
            }
        )
        observations.append(
            {
                "predicate": "http_status",
                "object_value": str(status_code),
                "observed_at": now.isoformat(),
                "confidence": 1.0,
            }
        )

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
