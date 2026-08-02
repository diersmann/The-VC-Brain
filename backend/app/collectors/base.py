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
