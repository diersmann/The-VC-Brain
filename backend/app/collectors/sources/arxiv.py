"""arXiv connector — discovers and collects paper/author data.

Lightweight: paper metadata + abstract.
Deep: full PDF download + coauthor expansion (capped).

Discovery includes relevant authors regardless of citation count. Citations are
retained as a confidence and momentum signal, not an eligibility gate.
"""

from __future__ import annotations

import asyncio
import io
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from pypdf import PdfReader

from app.collectors.base import (
    Collected,
    Connector,
    ConnectorError,
    Depth,
    Seed,
    canonical_json_bytes,
    normalize_connector_error,
)

logger = structlog.get_logger(__name__)

_ARXIV_API = "https://export.arxiv.org/api/query"
_SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
_DEFAULT_MAX_RESULTS = 50
_MAX_EVIDENCE_PAGES = 20
_MAX_PAGE_CHARS = 2000
_MAX_PDF_BYTES = 25 * 1024 * 1024
_ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"
_ATOM_FEED_TAG = f"{{{_ATOM_NAMESPACE}}}feed"
_ATOM_ENTRY_TAG = f"{{{_ATOM_NAMESPACE}}}entry"
_ATOM_FIELDS = {
    "author",
    "category",
    "contributor",
    "generator",
    "icon",
    "id",
    "link",
    "logo",
    "name",
    "published",
    "rights",
    "summary",
    "title",
    "updated",
}

# arXiv categories relevant to typical VC theses (configurable).
_DEFAULT_CATEGORIES = [
    "cs.AI",
    "cs.LG",
    "cs.CL",
    "cs.CV",
    "cs.SE",
    "cs.IR",
    "cs.NE",
    "cs.RO",
    "stat.ML",
]


class ArxivConnector(Connector):
    name = "arxiv"
    source_type = "arxiv"
    authority = 0.7
    cost = 2.0

    async def _client(self) -> httpx.AsyncClient:
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        return httpx.AsyncClient(limits=limits, timeout=30.0)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_atom_feed(payload: str | bytes, *, context: str) -> ET.Element:
        """Parse an arXiv response only when it is an exact Atom feed.

        ElementTree accepts unqualified tags and silently ignores entries in a
        different namespace when queried with an Atom namespace.  That can turn
        an HTML/error payload into a successful empty page, so the connector
        validates the root and every entry tag before extracting any fields.
        """
        try:
            root = ET.fromstring(payload)
        except (ET.ParseError, ValueError) as exc:
            raise ConnectorError(
                f"{context}: invalid provider response: malformed Atom XML"
            ) from exc

        if root.tag != _ATOM_FEED_TAG:
            raise ConnectorError(f"{context}: invalid provider response: expected Atom feed")

        # Reject an unqualified or foreign-namespace entry instead of silently
        # treating it as an empty result.  Atom extensions remain allowed.
        for element in root.iter():
            if element is root:
                continue
            if not isinstance(element.tag, str):
                continue
            local_name = element.tag.rsplit("}", 1)[-1]
            if local_name in _ATOM_FIELDS or local_name == "entry":
                expected_tag = f"{{{_ATOM_NAMESPACE}}}{local_name}"
                if element.tag != expected_tag:
                    field = "entry" if local_name == "entry" else local_name
                    raise ConnectorError(
                        f"{context}: invalid provider response: Atom {field} "
                        "is not in the Atom namespace"
                    )
        return root

    @staticmethod
    def _atom_required_text(
        element: ET.Element,
        field: str,
        *,
        context: str,
    ) -> str:
        value = element.findtext(f"{{{_ATOM_NAMESPACE}}}{field}", "").strip()
        if not value:
            raise ConnectorError(
                f"{context}: invalid provider response: Atom entry is missing {field}"
            )
        return value

    @staticmethod
    def _api_source_locator(
        source_uri: str,
        *,
        field: str,
        query: str,
        arxiv_id: str | None = None,
    ) -> dict[str, object]:
        locator: dict[str, object] = {
            "kind": "api_field",
            "source_uri": source_uri,
            "field": field,
            "query": query,
        }
        if arxiv_id:
            locator["arxiv_id"] = arxiv_id
        return locator

    async def discover(self, query: str, page: int = 1) -> list[Seed]:
        """Search arXiv by topic and return author seeds.

        Returns authors from relevant categories regardless of citation count.
        Citation counts remain metadata and are collected as a downstream signal.

        Args:
            query: Search topic.
            page: Page number (1-indexed, 50 results per page).
        """
        # Build arXiv search query
        cat_filter = " OR ".join(f"cat:{c}" for c in _DEFAULT_CATEGORIES)
        search_query = f"({query}) AND ({cat_filter})"
        start = (page - 1) * _DEFAULT_MAX_RESULTS
        params: dict[str, str | int] = {
            "search_query": f"all:{search_query}",
            "start": start,
            "max_results": _DEFAULT_MAX_RESULTS,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        try:
            async with await self._client() as client:
                resp = await client.get(_ARXIV_API, params=params)
        except Exception as exc:
            raise normalize_connector_error(exc, context="arxiv_search_failed") from exc

        if resp.status_code == 429:
            raise ConnectorError("arxiv_rate_limited: HTTP 429")
        if resp.status_code != 200:
            logger.error("arxiv_search_failed", status=resp.status_code)
            raise ConnectorError(f"arxiv_search_failed: HTTP {resp.status_code}")

        seeds: list[Seed] = []
        seen_authors: set[str] = set()

        root = self._parse_atom_feed(resp.content, context="arxiv_search_failed")
        ns = {"atom": _ATOM_NAMESPACE}
        source_uri = str(resp.url)

        for entry in root.findall("atom:entry", ns):
            entry_id = self._atom_required_text(
                entry,
                "id",
                context="arxiv_search_failed",
            )
            arxiv_id = entry_id.rstrip("/").split("/")[-1]
            if not arxiv_id:
                raise ConnectorError(
                    "arxiv_search_failed: invalid provider response: Atom entry has an empty id"
                )

            # Get citation count from Semantic Scholar
            citations = await self._fetch_citations(arxiv_id)
            authors = entry.findall("atom:author", ns)
            for author in authors:
                name = author.findtext(f"{{{_ATOM_NAMESPACE}}}name", "").strip()
                if name and name.lower() not in seen_authors:
                    seen_authors.add(name.lower())
                    seeds.append(
                        Seed(
                            source_type="arxiv",
                            handle=name,
                            display_hint=name,
                            metadata={
                                "arxiv_id": arxiv_id,
                                "citations": citations,
                                "citation_signal": "context_only",
                                "query": query,
                                "source_locator": self._api_source_locator(
                                    source_uri,
                                    field="author",
                                    query=query,
                                    arxiv_id=arxiv_id,
                                ),
                            },
                        )
                    )

        return seeds

    async def _fetch_citations(self, arxiv_id: str) -> int:
        """Fetch citation count from Semantic Scholar API."""
        async with await self._client() as client:
            try:
                resp = await client.get(
                    f"{_SEMANTIC_SCHOLAR_API}/paper/arXiv:{arxiv_id}",
                    params={"fields": "citationCount"},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    raw_citations = data.get("citationCount", 0)
                    if isinstance(raw_citations, int) and not isinstance(raw_citations, bool):
                        return max(raw_citations, 0)
                    logger.warning("semantic_scholar_invalid_citations", arxiv_id=arxiv_id)
            except Exception:
                logger.warning("semantic_scholar_failed", arxiv_id=arxiv_id)
        return 0

    @staticmethod
    def _extract_pdf_page_observations(
        pdf_bytes: bytes,
        *,
        pdf_url: str,
        author_name: str,
        observed_at: datetime,
        author_identity_confidence: float = 0.8,
    ) -> list[dict[str, object]]:
        """Extract bounded, page-addressable evidence from a deep PDF."""
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes), strict=True)
        except Exception as exc:
            logger.warning("arxiv_pdf_parse_failed", error=str(exc))
            return []

        observations: list[dict[str, object]] = []
        for page_number, page in enumerate(reader.pages, start=1):
            if page_number > _MAX_EVIDENCE_PAGES:
                break
            text: str
            reason: str | None
            try:
                extracted_text = page.extract_text() or ""
                text = extracted_text.strip()
            except Exception as exc:
                logger.warning("arxiv_pdf_page_extract_failed", page=page_number, error=str(exc))
                text = ""
                reason = "text_extraction_failed"
            else:
                reason = "no_extractable_text" if not text else None
            bounded_text = text[:_MAX_PAGE_CHARS] or "[No extractable text on page]"
            locator: dict[str, object] = {
                "kind": "pdf_page",
                "source_uri": pdf_url,
                "page": page_number,
                "char_start": 0,
                "char_end": len(text[:_MAX_PAGE_CHARS]),
                "author": author_name,
                "author_identity_confidence": author_identity_confidence,
            }
            if reason is not None:
                locator["reason"] = reason
            observations.append(
                {
                    "predicate": "arxiv_pdf_page_text",
                    "object_value": bounded_text,
                    "observed_at": observed_at.isoformat(),
                    "confidence": 0.9,
                    "source_locator": locator,
                }
            )
        return observations

    @staticmethod
    def _count_pdf_pages(pdf_bytes: bytes, *, max_pages: int) -> int:
        """Parse a bounded PDF in a worker thread and return its page count."""
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes), strict=True)
            if reader.is_encrypted:
                raise ConnectorError("arxiv_pdf_rejected: encrypted PDF")
            page_count = len(reader.pages)
        except ConnectorError:
            raise
        except Exception as exc:
            raise ConnectorError("arxiv_pdf_rejected: PDF could not be parsed safely") from exc
        if page_count < 1:
            raise ConnectorError("arxiv_pdf_rejected: PDF has no pages")
        if page_count > max_pages:
            raise ConnectorError(f"arxiv_pdf_rejected: PDF exceeds {max_pages}-page limit")
        return page_count

    @staticmethod
    def _validate_pdf_headers(
        response: httpx.Response,
        *,
        max_bytes: int,
    ) -> None:
        if response.status_code != 200:
            raise ConnectorError(f"arxiv_pdf_rejected: HTTP {response.status_code}")

        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/pdf":
            raise ConnectorError("arxiv_pdf_rejected: response is not application/pdf")

        declared_length = response.headers.get("content-length", "").strip()
        if declared_length.isdigit() and int(declared_length) > max_bytes:
            raise ConnectorError(f"arxiv_pdf_rejected: response exceeds {max_bytes}-byte limit")

    @classmethod
    async def _read_bounded_pdf_response(
        cls,
        client: httpx.AsyncClient,
        pdf_url: str,
        *,
        max_bytes: int = _MAX_PDF_BYTES,
    ) -> httpx.Response:
        """Stream a PDF response without buffering more than its byte cap."""
        async with client.stream("GET", pdf_url, timeout=60.0) as response:
            cls._validate_pdf_headers(response, max_bytes=max_bytes)
            chunks: list[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise ConnectorError(
                        f"arxiv_pdf_rejected: response exceeds {max_bytes}-byte limit"
                    )
                chunks.append(chunk)
            return httpx.Response(
                response.status_code,
                headers=response.headers,
                content=b"".join(chunks),
                request=response.request,
            )

    @classmethod
    async def _validate_pdf_response(
        cls,
        response: httpx.Response,
        *,
        max_bytes: int = _MAX_PDF_BYTES,
        max_pages: int = _MAX_EVIDENCE_PAGES,
    ) -> bytes:
        """Validate response metadata and parse a bounded PDF off the event loop."""
        cls._validate_pdf_headers(response, max_bytes=max_bytes)
        pdf_bytes = response.content
        if len(pdf_bytes) > max_bytes:
            raise ConnectorError(f"arxiv_pdf_rejected: response exceeds {max_bytes}-byte limit")
        if not pdf_bytes.startswith(b"%PDF-"):
            raise ConnectorError("arxiv_pdf_rejected: response does not have PDF magic bytes")

        await asyncio.to_thread(cls._count_pdf_pages, pdf_bytes, max_pages=max_pages)
        return pdf_bytes

    # ------------------------------------------------------------------
    # Collect
    # ------------------------------------------------------------------

    async def collect(self, seed: Seed, depth: Depth = "light") -> Collected:
        author_name = seed.handle
        observations: list[dict[str, object]] = []
        now = datetime.now(UTC)

        # Search arXiv for papers by this author
        params: dict[str, str | int] = {
            "search_query": f'au:"{author_name}"',
            "start": 0,
            "max_results": 50,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        async with await self._client() as client:
            resp = await client.get(_ARXIV_API, params=params)

        if resp.status_code != 200:
            raise ConnectorError(f"arxiv_author_fetch_failed: {resp.status_code}")

        root = self._parse_atom_feed(resp.content, context="arxiv_author_fetch_failed")
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        source_uri = str(resp.url)

        papers: list[dict[str, Any]] = []
        coauthors: set[str] = set()
        total_citations = 0
        paper_count = 0

        for entry in root.findall("atom:entry", ns):
            entry_id = self._atom_required_text(
                entry,
                "id",
                context="arxiv_author_fetch_failed",
            )
            arxiv_id = entry_id.rstrip("/").split("/")[-1]
            if not arxiv_id:
                raise ConnectorError(
                    "arxiv_author_fetch_failed: invalid provider response: "
                    "Atom entry has an empty id"
                )
            title = entry.findtext("atom:title", "", ns).strip()
            summary = entry.findtext("atom:summary", "", ns).strip()
            published = entry.findtext("atom:published", "", ns) or ""

            # Categories
            categories = []
            for cat in entry.findall("atom:category", ns):
                term = cat.get("term", "")
                if term:
                    categories.append(term)

            # Authors
            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.findtext("atom:name", "", ns)
                if name:
                    authors.append(name)
                    if name.lower() != author_name.lower():
                        coauthors.add(name)

            # Citation count
            citations = await self._fetch_citations(arxiv_id)
            total_citations += citations
            paper_count += 1

            papers.append(
                {
                    "arxiv_id": arxiv_id,
                    "title": title,
                    "summary": summary[:2000],
                    "published": published,
                    "categories": categories,
                    "authors": authors,
                    "citations": citations,
                }
            )

        observations.append(
            {
                "predicate": "arxiv_paper_count",
                "object_value": str(paper_count),
                "observed_at": now.isoformat(),
                "confidence": 1.0,
                "source_locator": self._api_source_locator(
                    source_uri,
                    field="paper_count",
                    query=author_name,
                ),
            }
        )
        observations.append(
            {
                "predicate": "arxiv_total_citations",
                "object_value": str(total_citations),
                "observed_at": now.isoformat(),
                "confidence": 0.8,
                "source_locator": self._api_source_locator(
                    source_uri,
                    field="total_citations",
                    query=author_name,
                ),
            }
        )
        observations.append(
            {
                "predicate": "arxiv_coauthors",
                "object_value": ",".join(sorted(coauthors)) or "[No coauthors found]",
                "observed_at": now.isoformat(),
                "confidence": 0.7,
                "source_locator": self._api_source_locator(
                    source_uri,
                    field="coauthors",
                    query=author_name,
                ),
            }
        )

        # Deep: download full PDF for the most cited paper
        if depth == "deep" and papers:
            # Sort by citations descending, pick top paper
            papers.sort(key=lambda p: p.get("citations", 0), reverse=True)
            top_paper = papers[0]
            pdf_url = f"https://arxiv.org/pdf/{top_paper['arxiv_id']}.pdf"
            try:
                async with await self._client() as pdf_client:
                    pdf_resp = await self._read_bounded_pdf_response(pdf_client, pdf_url)
                pdf_bytes = await self._validate_pdf_response(pdf_resp)
                if pdf_bytes:
                    observations.extend(
                        await asyncio.to_thread(
                            self._extract_pdf_page_observations,
                            pdf_bytes,
                            pdf_url=pdf_url,
                            author_name=author_name,
                            observed_at=now,
                            author_identity_confidence=(
                                0.8
                                if any(
                                    name.lower() == author_name.lower()
                                    for name in top_paper.get("authors", [])
                                )
                                else 0.0
                            ),
                        )
                    )
                    return Collected(
                        content=pdf_bytes,
                        content_type="application/pdf",
                        observations=observations,
                        source_type="arxiv",
                        uri=pdf_url,
                        license_hint={
                            "source": "arXiv PDF",
                            "terms": "https://info.arxiv.org/help/api/tou.html",
                            "evidence_depth": "page_coordinates",
                        },
                    )
            except ConnectorError:
                raise
            except Exception as exc:
                logger.warning(
                    "arxiv_pdf_download_failed",
                    arxiv_id=top_paper["arxiv_id"],
                    error_type=type(exc).__name__,
                )

        raw_bytes = canonical_json_bytes(papers)
        return Collected(
            content=raw_bytes,
            content_type="application/json",
            observations=observations,
            source_type="arxiv",
            uri=source_uri,
            license_hint={"source": "arXiv API", "terms": "https://info.arxiv.org/help/api/tou.html"},
        )
