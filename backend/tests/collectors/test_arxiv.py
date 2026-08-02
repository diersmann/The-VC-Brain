"""Tests for arXiv discovery eligibility and provenance."""

from unittest.mock import AsyncMock

import pytest
import respx
from httpx import Response

from app.collectors.sources.arxiv import ArxivConnector


@pytest.mark.asyncio
@respx.mock
async def test_uncited_recent_author_remains_discoverable() -> None:
    route = respx.get("https://export.arxiv.org/api/query").mock(
        return_value=Response(
            200,
            text='''<?xml version="1.0" encoding="UTF-8"?>
            <feed xmlns="http://www.w3.org/2005/Atom">
              <entry>
                <id>http://arxiv.org/abs/2608.00001</id>
                <author><name>Ada Founder</name></author>
              </entry>
            </feed>''',
        )
    )
    connector = ArxivConnector()
    connector._fetch_citations = AsyncMock(return_value=0)  # type: ignore[method-assign]

    seeds = await connector.discover("robotics")

    assert route.called
    assert len(seeds) == 1
    assert seeds[0].handle == "Ada Founder"
    assert seeds[0].metadata["citations"] == 0
    assert seeds[0].metadata["citation_signal"] == "context_only"
