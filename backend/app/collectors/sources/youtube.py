"""YouTube connector — discovers founders via YouTube Data API v3.

Free tier: 10,000 quota units/day.  A search costs 100 units.
No transcription in MVP (that's Phase 3 — would need Whisper or YouTube transcript API).

Discovery: search for talks, demos, and interviews by topic.
Collect: channel metadata + recent video titles/descriptions.
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

_API_BASE = "https://www.googleapis.com/youtube/v3"
_DEFAULT_MAX_RESULTS = 20


class YouTubeConnector(Connector):
    name = "youtube"
    source_type = "youtube"
    authority = 0.5
    cost = 3.0

    def __init__(self) -> None:
        self._api_key: str | None = None

    def _get_api_key(self) -> str:
        if self._api_key:
            return self._api_key
        from app.config import get_settings

        settings = get_settings()
        self._api_key = settings.youtube_api_key
        if not self._api_key:
            logger.warning("youtube_api_key_not_configured")
        return self._api_key or ""

    async def _client(self) -> httpx.AsyncClient:
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        return httpx.AsyncClient(limits=limits, timeout=15.0)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def discover(self, query: str, page: int = 1) -> list[Seed]:
        """Search YouTube for videos matching the query, return channel seeds.

        Returns channels (not individual videos) so we can collect the
        channel's full metadata and recent uploads.

        Args:
            query: Search topic.
            page: Page number (1-indexed, 20 results per page).
        """
        api_key = self._get_api_key()
        if not api_key:
            logger.warning("youtube_discover_skipped_no_key")
            return []

        seeds: list[Seed] = []
        seen_channels: set[str] = set()

        params: dict[str, str | int] = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": _DEFAULT_MAX_RESULTS,
            "key": api_key,
        }
        # YouTube uses pageToken (string), not page numbers.
        # For MVP, we skip pagination and just use the first page.
        # Phase 2: track pageToken in Redis.

        async with await self._client() as client:
            resp = await client.get(f"{_API_BASE}/search", params=params)

        if resp.status_code != 200:
            logger.error("youtube_search_failed", status=resp.status_code)
            return []

        data = resp.json()
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            channel_id = snippet.get("channelId", "")
            channel_title = snippet.get("channelTitle", "")

            if channel_id and channel_id not in seen_channels:
                seen_channels.add(channel_id)
                seeds.append(
                    Seed(
                        source_type="youtube",
                        handle=channel_id,
                        display_hint=channel_title or channel_id,
                        metadata={
                            "query": query,
                            "channel_title": channel_title,
                            "video_title": snippet.get("title", ""),
                        },
                    )
                )

        return seeds

    # ------------------------------------------------------------------
    # Collect
    # ------------------------------------------------------------------

    async def collect(self, seed: Seed, depth: Depth = "light") -> Collected:
        channel_id = seed.handle
        api_key = self._get_api_key()
        observations: list[dict[str, object]] = []
        now = datetime.now(UTC)

        if not api_key:
            raise ConnectorError("youtube_api_key_not_configured")

        async with await self._client() as client:
            # 1. Channel metadata
            channel_resp = await client.get(
                f"{_API_BASE}/channels",
                params={
                    "part": "snippet,statistics",
                    "id": channel_id,
                    "key": api_key,
                },
            )
            if channel_resp.status_code != 200:
                raise ConnectorError(f"youtube_channel_fetch_failed: {channel_resp.status_code}")

            channel_data = channel_resp.json()
            channel_info = channel_data.get("items", [{}])[0] if channel_data.get("items") else {}
            snippet = channel_info.get("snippet", {})
            stats = channel_info.get("statistics", {})

            channel_title = snippet.get("title", "")
            channel_description = snippet.get("description", "")
            subscriber_count = stats.get("subscriberCount", "0")
            video_count = stats.get("videoCount", "0")
            view_count = stats.get("viewCount", "0")

            observations.append(
                {
                    "predicate": "youtube_channel_id",
                    "object_value": channel_id,
                    "observed_at": now.isoformat(),
                    "confidence": 1.0,
                }
            )
            if channel_title:
                observations.append(
                    {
                        "predicate": "youtube_channel_title",
                        "object_value": channel_title,
                        "observed_at": now.isoformat(),
                        "confidence": 1.0,
                    }
                )
            if channel_description:
                observations.append(
                    {
                        "predicate": "youtube_channel_description",
                        "object_value": channel_description[:2000],
                        "observed_at": now.isoformat(),
                        "confidence": 0.8,
                    }
                )
            observations.append(
                {
                    "predicate": "youtube_subscriber_count",
                    "object_value": subscriber_count,
                    "observed_at": now.isoformat(),
                    "confidence": 1.0,
                }
            )
            observations.append(
                {
                    "predicate": "youtube_video_count",
                    "object_value": video_count,
                    "observed_at": now.isoformat(),
                    "confidence": 1.0,
                }
            )
            observations.append(
                {
                    "predicate": "youtube_view_count",
                    "object_value": view_count,
                    "observed_at": now.isoformat(),
                    "confidence": 1.0,
                }
            )

            # 2. Recent videos
            limit = 50 if depth == "deep" else 20
            videos_resp = await client.get(
                f"{_API_BASE}/search",
                params={
                    "part": "snippet",
                    "channelId": channel_id,
                    "order": "date",
                    "maxResults": limit,
                    "type": "video",
                    "key": api_key,
                },
            )

            videos: list[dict[str, Any]] = []
            if videos_resp.status_code == 200:
                videos = videos_resp.json().get("items", [])

            video_titles = [
                v.get("snippet", {}).get("title", "")
                for v in videos
                if v.get("snippet", {}).get("title")
            ]
            if video_titles:
                observations.append(
                    {
                        "predicate": "youtube_recent_videos",
                        "object_value": " | ".join(video_titles[:10]),
                        "observed_at": now.isoformat(),
                        "confidence": 0.9,
                    }
                )

        raw_bytes = canonical_json_bytes({"channel": channel_info, "videos": videos})
        return Collected(
            content=raw_bytes,
            content_type="application/json",
            observations=observations,
            source_type="youtube",
            uri=f"https://www.youtube.com/channel/{channel_id}",
            license_hint={
                "source": "YouTube Data API v3",
                "terms": "https://developers.google.com/youtube/terms",
            },
        )
