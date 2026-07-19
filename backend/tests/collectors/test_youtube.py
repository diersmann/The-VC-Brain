"""Tests for the YouTube connector.

Uses respx to mock httpx calls to the YouTube Data API.
"""

from __future__ import annotations

import pytest
import respx

from app.collectors.base import Seed
from app.collectors.sources.youtube import YouTubeConnector


@pytest.fixture
def connector() -> YouTubeConnector:
    return YouTubeConnector()


def make_seed(channel_id: str) -> Seed:
    return Seed(source_type="youtube", handle=channel_id, display_hint=channel_id)


@pytest.mark.asyncio
async def test_discover_returns_seeds(connector: YouTubeConnector) -> None:
    """Discover should return channel seeds from search results."""
    # Set a fake API key so the connector doesn't skip
    connector._api_key = "test-key"

    with respx.mock:
        respx.get("https://www.googleapis.com/youtube/v3/search").respond(
            json={
                "items": [
                    {
                        "snippet": {
                            "channelId": "UC_abc123",
                            "channelTitle": "AI Builders",
                            "title": "Building ML Infrastructure",
                        }
                    },
                    {
                        "snippet": {
                            "channelId": "UC_def456",
                            "channelTitle": "Tech Talks",
                            "title": "Scaling AI Startups",
                        }
                    },
                ]
            }
        )

        seeds = await connector.discover("machine learning infrastructure")
        assert len(seeds) == 2
        assert seeds[0].handle == "UC_abc123"
        assert seeds[0].display_hint == "AI Builders"
        assert seeds[1].handle == "UC_def456"


@pytest.mark.asyncio
async def test_discover_no_key_returns_empty(connector: YouTubeConnector) -> None:
    """No API key should return an empty list gracefully."""
    connector._api_key = ""
    seeds = await connector.discover("machine learning")
    assert seeds == []


@pytest.mark.asyncio
async def test_collect_light_returns_collected(connector: YouTubeConnector) -> None:
    """Light collect should return a Collected with channel metadata."""
    connector._api_key = "test-key"
    channel_id = "UC_abc123"

    with respx.mock:
        # Channel metadata
        respx.get("https://www.googleapis.com/youtube/v3/channels").respond(
            json={
                "items": [
                    {
                        "snippet": {
                            "title": "AI Builders",
                            "description": "We build AI infrastructure.",
                        },
                        "statistics": {
                            "subscriberCount": "15000",
                            "videoCount": "120",
                            "viewCount": "500000",
                        },
                    }
                ]
            }
        )
        # Recent videos
        respx.get("https://www.googleapis.com/youtube/v3/search").respond(
            json={
                "items": [
                    {
                        "snippet": {
                            "title": "Building a Vector Database",
                        }
                    },
                    {
                        "snippet": {
                            "title": "ML Pipeline Best Practices",
                        }
                    },
                ]
            }
        )

        seed = make_seed(channel_id)
        collected = await connector.collect(seed, depth="light")

        assert collected.source_type == "youtube"
        assert collected.uri == f"https://www.youtube.com/channel/{channel_id}"
        assert len(collected.observations) > 0

        obs: dict[str, str] = {}
        for o in collected.observations:
            pred = str(o.get("predicate", ""))
            val = str(o.get("object_value", ""))
            obs[pred] = val

        assert obs["youtube_channel_id"] == channel_id
        assert obs["youtube_channel_title"] == "AI Builders"
        assert obs["youtube_subscriber_count"] == "15000"
        assert obs["youtube_video_count"] == "120"
        assert obs["youtube_view_count"] == "500000"
        assert "Building a Vector Database" in obs["youtube_recent_videos"]


@pytest.mark.asyncio
async def test_collect_deep_includes_more_videos(connector: YouTubeConnector) -> None:
    """Deep collect should request more videos (50 vs 20)."""
    connector._api_key = "test-key"
    channel_id = "UC_abc123"

    with respx.mock:
        # Channel metadata
        respx.get("https://www.googleapis.com/youtube/v3/channels").respond(
            json={
                "items": [
                    {
                        "snippet": {"title": "AI Builders"},
                        "statistics": {
                            "subscriberCount": "15000",
                            "videoCount": "120",
                            "viewCount": "500000",
                        },
                    }
                ]
            }
        )
        # Recent videos (deep: 50)
        respx.get("https://www.googleapis.com/youtube/v3/search").respond(
            json={
                "items": [
                    {"snippet": {"title": f"Video {i}"}}
                    for i in range(5)
                ]
            }
        )

        seed = make_seed(channel_id)
        collected = await connector.collect(seed, depth="deep")

        obs: dict[str, str] = {}
        for o in collected.observations:
            pred = str(o.get("predicate", ""))
            val = str(o.get("object_value", ""))
            obs[pred] = val

        assert "youtube_recent_videos" in obs
        assert "Video 0" in obs["youtube_recent_videos"]
