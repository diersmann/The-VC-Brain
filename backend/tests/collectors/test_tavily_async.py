"""Regression coverage for non-blocking Tavily discovery calls."""

from __future__ import annotations

import threading
from typing import Any

import pytest

from app.collectors.sources.hackathons import HackathonsConnector
from app.collectors.sources.linkedin import LinkedInConnector
from app.collectors.sources.podcasts import PodcastsConnector
from app.collectors.sources.tavily_search import TavilySearchConnector


class _SyncTavily:
    def __init__(self) -> None:
        self.call_threads: list[int] = []

    def search(self, **_kwargs: object) -> dict[str, list[dict[str, str]]]:
        self.call_threads.append(threading.get_ident())
        return {
            "results": [
                {
                    "url": "https://linkedin.com/in/founder",
                    "title": "Ada Lovelace - LinkedIn",
                    "content": "Ada Lovelace founder of Example",
                }
            ]
        }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "connector_type",
    [TavilySearchConnector, LinkedInConnector, PodcastsConnector, HackathonsConnector],
)
async def test_tavily_discovery_runs_sync_sdk_off_event_loop(
    connector_type: type[Any],
) -> None:
    connector = connector_type()
    tavily = _SyncTavily()
    connector._client = tavily if connector_type is TavilySearchConnector else None
    connector._tavily = tavily if connector_type is not TavilySearchConnector else None
    if connector_type is not TavilySearchConnector:
        connector._get_tavily = lambda: tavily
    else:
        connector._get_client = lambda: tavily

    event_loop_thread = threading.get_ident()
    seeds = await connector.discover("AI founders")

    assert seeds
    assert tavily.call_threads
    assert all(thread_id != event_loop_thread for thread_id in tavily.call_threads)
