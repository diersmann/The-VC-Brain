"""Tests for arXiv discovery eligibility and provenance."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
from httpx import Response

from app.collectors.sources.arxiv import ArxivConnector


def test_deep_pdf_evidence_has_page_coordinates_and_identity_confidence() -> None:
    page = MagicMock()
    page.extract_text.return_value = "A primary result on page one."
    reader = MagicMock()
    reader.pages = [page]

    with patch("app.collectors.sources.arxiv.PdfReader", return_value=reader):
        observations = ArxivConnector._extract_pdf_page_observations(
            b"%PDF-1.7",
            pdf_url="https://arxiv.org/pdf/2608.00001.pdf",
            author_name="Ada Founder",
            observed_at=datetime(2026, 8, 3, tzinfo=UTC),
        )

    assert observations == [
        {
            "predicate": "arxiv_pdf_page_text",
            "object_value": "A primary result on page one.",
            "observed_at": "2026-08-03T00:00:00+00:00",
            "confidence": 0.9,
            "source_locator": {
                "kind": "pdf_page",
                "source_uri": "https://arxiv.org/pdf/2608.00001.pdf",
                "page": 1,
                "char_start": 0,
                "char_end": 29,
                "author": "Ada Founder",
                "author_identity_confidence": 0.8,
            },
        }
    ]


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
