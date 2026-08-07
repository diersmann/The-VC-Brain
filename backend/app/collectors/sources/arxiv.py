"""arXiv connector — discovers and collects paper/author data.

Lightweight: paper metadata + abstract.
Deep: full PDF download + coauthor expansion (capped).

Discovery includes relevant authors regardless of citation count. Citations are
retained as a confidence and momentum signal, not an eligibility gate.
"""

from __future__ import annotations

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
)

logger = structlog.get_logger(__name__)

_ARXIV_API = "https://export.arxiv.org/api/query"
_SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
_DEFAULT_MAX_RESULTS = 50
_MAX_EVIDENCE_PAGES = 20
_MAX_PAGE_CHARS = 2000

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

        async with await self._client() as client:
            resp = await client.get(_ARXIV_API, params=params)

        if resp.status_code == 429:
            raise ConnectorError("arxiv_rate_limited: HTTP 429")
        if resp.status_code != 200:
            logger.error("arxiv_search_failed", status=resp.status_code)
            return []

        seeds: list[Seed] = []
        seen_authors: set[str] = set()

        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", ns):
            arxiv_id = entry.findtext("atom:id", "", ns).split("/")[-1]

            # Get citation count from Semantic Scholar
            citations = await self._fetch_citations(arxiv_id)
            authors = entry.findall("atom:author", ns)
            for author in authors:
                name = author.findtext("atom:name", "", ns)
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
                    citations: int = data.get("citationCount", 0)
                    return citations
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
    ) -> list[dict[str, object]]:
        """Extract bounded, page-addressable evidence from a deep PDF."""
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
        except Exception as exc:
            logger.warning("arxiv_pdf_parse_failed", error=str(exc))
            return []

        observations: list[dict[str, object]] = []
        for page_number, page in enumerate(reader.pages, start=1):
            if page_number > _MAX_EVIDENCE_PAGES:
                break
            try:
                text = (page.extract_text() or "").strip()
            except Exception as exc:
                logger.warning("arxiv_pdf_page_extract_failed", page=page_number, error=str(exc))
                continue
            if not text:
                continue
            bounded_text = text[:_MAX_PAGE_CHARS]
            observations.append(
                {
                    "predicate": "arxiv_pdf_page_text",
                    "object_value": bounded_text,
                    "observed_at": observed_at.isoformat(),
                    "confidence": 0.9,
                    "source_locator": {
                        "kind": "pdf_page",
                        "source_uri": pdf_url,
                        "page": page_number,
                        "char_start": 0,
                        "char_end": len(bounded_text),
                        "author": author_name,
                        "author_identity_confidence": 0.8,
                    },
                }
            )
        return observations

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

        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        papers: list[dict[str, Any]] = []
        coauthors: set[str] = set()
        total_citations = 0
        paper_count = 0

        for entry in root.findall("atom:entry", ns):
            arxiv_id = entry.findtext("atom:id", "", ns).split("/")[-1]
            title = entry.findtext("atom:title", "", ns).strip()
            summary = entry.findtext("atom:summary", "", ns).strip()
            published = entry.findtext("atom:published", "", ns)

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
            }
        )
        observations.append(
            {
                "predicate": "arxiv_total_citations",
                "object_value": str(total_citations),
                "observed_at": now.isoformat(),
                "confidence": 0.8,
            }
        )
        observations.append(
            {
                "predicate": "arxiv_coauthors",
                "object_value": ",".join(sorted(coauthors)),
                "observed_at": now.isoformat(),
                "confidence": 0.7,
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
                    pdf_resp = await pdf_client.get(pdf_url, timeout=60.0)
                if pdf_resp.status_code == 200:
                    pdf_bytes = pdf_resp.content
                    observations.extend(
                        self._extract_pdf_page_observations(
                            pdf_bytes,
                            pdf_url=pdf_url,
                            author_name=author_name,
                            observed_at=now,
                        )
                    )
                    if pdf_bytes:
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
            except Exception:
                logger.warning("arxiv_pdf_download_failed", arxiv_id=top_paper["arxiv_id"])

        raw_bytes = canonical_json_bytes(papers)
        return Collected(
            content=raw_bytes,
            content_type="application/json",
            observations=observations,
            source_type="arxiv",
            uri=f"https://arxiv.org/search/?query={author_name}&searchtype=author",
            license_hint={"source": "arXiv API", "terms": "https://info.arxiv.org/help/api/tou.html"},
        )
