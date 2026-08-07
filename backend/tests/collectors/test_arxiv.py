"""Tests for arXiv discovery eligibility and provenance."""

import asyncio
import io
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx
from httpx import Response
from pypdf import PdfWriter

from app.collectors.base import ConnectorError, Seed
from app.collectors.sources.arxiv import ArxivConnector


def _pdf_bytes(*, pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


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


def test_deep_pdf_evidence_preserves_no_text_page_provenance() -> None:
    page = MagicMock()
    page.extract_text.return_value = ""
    reader = MagicMock()
    reader.pages = [page]

    with patch("app.collectors.sources.arxiv.PdfReader", return_value=reader):
        observations = ArxivConnector._extract_pdf_page_observations(
            b"%PDF-1.7",
            pdf_url="https://arxiv.org/pdf/2608.00001.pdf",
            author_name="Ada Founder",
            observed_at=datetime(2026, 8, 3, tzinfo=UTC),
        )

    assert observations[0]["object_value"] == "[No extractable text on page]"
    assert observations[0]["source_locator"] == {
        "kind": "pdf_page",
        "source_uri": "https://arxiv.org/pdf/2608.00001.pdf",
        "page": 1,
        "char_start": 0,
        "char_end": 0,
        "author": "Ada Founder",
        "author_identity_confidence": 0.8,
        "reason": "no_extractable_text",
    }


def test_atom_feed_requires_exact_atom_namespace() -> None:
    with pytest.raises(ConnectorError, match="expected Atom feed"):
        ArxivConnector._parse_atom_feed(
            b"<feed><entry><id>https://arxiv.org/abs/2608.00001</id></entry></feed>",
            context="test",
        )

    with pytest.raises(ConnectorError, match="entry is not in the Atom namespace"):
        ArxivConnector._parse_atom_feed(
            b'<feed xmlns="http://www.w3.org/2005/Atom"><entry xmlns=""><id>x</id></entry></feed>',
            context="test",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "message"),
    [
        (
            Response(
                503,
                content=_pdf_bytes(),
                headers={"content-type": "application/pdf"},
            ),
            "HTTP 503",
        ),
        (
            Response(
                200,
                content=_pdf_bytes(),
                headers={"content-type": "text/html"},
            ),
            "application/pdf",
        ),
        (
            Response(
                200,
                content=b"not a PDF",
                headers={"content-type": "application/pdf"},
            ),
            "magic bytes",
        ),
    ],
)
async def test_pdf_response_rejects_status_mime_and_magic(
    response: Response,
    message: str,
) -> None:
    with pytest.raises(ConnectorError, match=message):
        await ArxivConnector._validate_pdf_response(response)


@pytest.mark.asyncio
async def test_pdf_response_enforces_byte_and_page_limits_and_offloads_reader() -> None:
    pdf = _pdf_bytes(pages=2)
    response = Response(
        200,
        content=pdf,
        headers={"content-type": "application/pdf"},
    )

    with pytest.raises(ConnectorError, match="byte limit"):
        await ArxivConnector._validate_pdf_response(response, max_bytes=len(pdf) - 1)

    with pytest.raises(ConnectorError, match="page limit"):
        await ArxivConnector._validate_pdf_response(response, max_pages=1)

    with patch(
        "app.collectors.sources.arxiv.asyncio.to_thread",
        wraps=asyncio.to_thread,
    ) as offload:
        assert await ArxivConnector._validate_pdf_response(response) == pdf
    assert offload.call_count == 1


@pytest.mark.asyncio
async def test_pdf_stream_stops_after_bounded_body() -> None:
    class StreamingResponse:
        def __init__(self) -> None:
            self.status_code = 200
            self.headers = {"content-type": "application/pdf"}
            self.request = httpx.Request("GET", "https://arxiv.org/pdf/test.pdf")

        async def __aenter__(self) -> "StreamingResponse":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def aiter_bytes(self, *, chunk_size: int) -> object:
            assert chunk_size == 64 * 1024
            yield b"%PDF"
            yield b"-1.7\n"  # The second chunk crosses the configured cap.

    class StreamingClient:
        def stream(self, *_args: object, **_kwargs: object) -> StreamingResponse:
            return StreamingResponse()

    with pytest.raises(ConnectorError, match="byte limit"):
        await ArxivConnector._read_bounded_pdf_response(
            StreamingClient(),  # type: ignore[arg-type]
            "https://arxiv.org/pdf/test.pdf",
            max_bytes=4,
        )


@pytest.mark.asyncio
async def test_collect_preserves_api_metadata_locators_without_provider() -> None:
    feed = """<feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>https://arxiv.org/abs/2608.00001</id>
        <author><name>Ada Founder</name></author>
      </entry>
    </feed>"""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.get = AsyncMock(
        return_value=Response(
            200,
            text=feed,
            request=httpx.Request("GET", "https://export.arxiv.org/api/query"),
        )
    )
    connector = ArxivConnector()
    connector._client = AsyncMock(return_value=client)  # type: ignore[method-assign]
    connector._fetch_citations = AsyncMock(return_value=0)  # type: ignore[method-assign]

    collected = await connector.collect(seed=Seed("arxiv", "Ada Founder"))

    assert all(
        observation["source_locator"]["kind"] == "api_field"
        for observation in collected.observations
        if observation["predicate"].startswith("arxiv_")
        and observation["predicate"] != "arxiv_pdf_page_text"
    )
    assert collected.uri == collected.observations[0]["source_locator"]["source_uri"]


@pytest.mark.asyncio
async def test_deep_collect_propagates_rejected_pdf() -> None:
    feed = """<feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>https://arxiv.org/abs/2608.00001</id>
        <author><name>Ada Founder</name></author>
      </entry>
    </feed>"""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.get = AsyncMock(
        return_value=Response(
            200,
            text=feed,
            request=httpx.Request("GET", "https://export.arxiv.org/api/query"),
        )
    )
    connector = ArxivConnector()
    connector._client = AsyncMock(return_value=client)  # type: ignore[method-assign]
    connector._fetch_citations = AsyncMock(return_value=1)  # type: ignore[method-assign]
    connector._read_bounded_pdf_response = AsyncMock(  # type: ignore[method-assign]
        side_effect=ConnectorError("arxiv_pdf_rejected: HTTP 503")
    )

    with pytest.raises(ConnectorError, match="HTTP 503"):
        await connector.collect(
            seed=Seed("arxiv", "Ada Founder"),
            depth="deep",
        )


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
