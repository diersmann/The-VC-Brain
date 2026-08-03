"""Connector protocol and shared types for the data collector.

Each source (GitHub, Product Hunt, arXiv, web, etc.) implements the
``Connector`` protocol.  A connector has two phases:

* ``discover(query)`` — cheap, returns candidate seeds (handles, URLs).
* ``collect(seed, depth)`` — fetches raw content and returns structured
  observations.  ``depth="light"`` is metadata-only; ``depth="deep"``
  fetches full content (READMEs, PDFs, transcripts, etc.).

The scheduler uses the ``cost`` and ``authority`` attributes to compute
collection priority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

Depth = Literal["light", "deep"]
ConnectorMaturity = Literal["experimental", "beta", "production"]


@dataclass(frozen=True)
class ConnectorReadiness:
    """Operator-facing maturity metadata for a registered connector."""

    maturity: ConnectorMaturity
    contract_version: str = "connector-contract-v1"
    last_success_at: str | None = None
    limitations: tuple[str, ...] = ()


CONNECTOR_READINESS: dict[str, ConnectorReadiness] = {
    "github": ConnectorReadiness("beta", limitations=("API credentials and rate limits apply",)),
    "producthunt": ConnectorReadiness("experimental", limitations=("API credentials required",)),
    "arxiv": ConnectorReadiness("beta", limitations=("PDF extraction depth varies by document",)),
    "web": ConnectorReadiness("beta", limitations=("Robots, licensing, and page structure vary",)),
    "tavily_search": ConnectorReadiness(
        "experimental", limitations=("Search provider and budget dependent",)
    ),
    "hackernews": ConnectorReadiness("beta", limitations=("Algolia result freshness varies",)),
    "youtube": ConnectorReadiness(
        "experimental", limitations=("API credentials and transcript availability apply",)
    ),
    "podcasts": ConnectorReadiness(
        "experimental", limitations=("Transcript and primary-page coverage varies",)
    ),
    "hackathons": ConnectorReadiness(
        "experimental", limitations=("Discovery delegates to provider search",)
    ),
    "linkedin": ConnectorReadiness(
        "experimental", limitations=("Discovery delegates to provider search",)
    ),
}


def canonical_json_bytes(value: object) -> bytes:
    """Serialize JSON snapshots deterministically and without Python repr syntax."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


@dataclass(frozen=True)
class Seed:
    """A typed target for collection.

    Attributes:
        source_type:  Connector name (e.g. ``"github"``, ``"arxiv"``).
        handle:      The identifier within that source (login, paper ID, URL).
        display_hint: Human-readable name for logging / Person stub.
        metadata:    Extra context (e.g. thesis query that produced this seed).
    """

    source_type: str
    handle: str
    display_hint: str = ""
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Collected:
    """Result of a successful ``collect()`` call.

    Attributes:
        content:       Raw bytes of the fetched material.
        content_type:  MIME type (``"application/json"``, ``"text/markdown"``, etc.).
        observations:  Structured observations extracted from the content.
                       Each is a dict with keys: subject_id, predicate,
                       object_value, observed_at, confidence.
        source_type:   Connector name.
        uri:           Original URI that was fetched.
        license_hint:  Optional license / terms metadata.
    """

    content: bytes
    content_type: str
    observations: list[dict[str, object]]
    source_type: str
    uri: str
    license_hint: dict[str, object] | None = None


@runtime_checkable
class Connector(Protocol):
    """Protocol that every source connector must satisfy."""

    name: str
    source_type: str
    authority: float  # 0.0 (low) - 1.0 (high)
    cost: float  # relative cost per collect call (used in priority math)

    async def discover(self, query: str, page: int = 1) -> list[Seed]:
        """Return candidate seeds for a discovery query.

        This should be cheap — metadata-only API calls, no full fetches.

        Args:
            query: Search query string.
            page: Page number for paginated sources (1-indexed).
        """
        ...

    async def collect(self, seed: Seed, depth: Depth = "light") -> Collected:
        """Fetch raw content and extract observations at the requested depth.

        Raises:
            ConnectorError: on transient or permanent failure.
        """
        ...


class ConnectorError(Exception):
    """Base exception for connector failures."""


def validate_collected(collected: Collected) -> None:
    """Validate the shared output contract before persistence or scoring."""
    if not collected.content:
        raise ConnectorError("connector returned empty content")
    if not collected.content_type.strip():
        raise ConnectorError("connector returned an empty content type")
    if not collected.source_type.strip():
        raise ConnectorError("connector returned an empty source type")
    if not collected.uri.strip():
        raise ConnectorError("connector returned an empty source URI")
    if not isinstance(collected.observations, list):
        raise ConnectorError("connector observations must be a list")
    for observation in collected.observations:
        if not isinstance(observation, dict):
            raise ConnectorError("connector observations must be objects")
        if not str(observation.get("predicate", "")).strip():
            raise ConnectorError("connector observation is missing predicate")
        if "object_value" not in observation:
            raise ConnectorError("connector observation is missing object_value")


FailureKind = Literal["transient", "rate_limited", "permanent"]


def classify_connector_failure(exc: BaseException) -> tuple[FailureKind, bool]:
    """Classify an upstream failure for retry and operator-facing state."""
    message = str(exc).lower()
    if any(token in message for token in ("429", "rate limit", "rate_limited", "throttl")):
        return "rate_limited", True
    if any(
        token in message
        for token in (
            "timeout",
            "timed out",
            "connection reset",
            "temporarily unavailable",
            "502",
            "503",
            "504",
        )
    ):
        return "transient", True
    return "permanent", False
