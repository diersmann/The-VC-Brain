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
from datetime import datetime
from typing import Literal, Protocol, runtime_checkable

Depth = Literal["light", "deep"]
ConnectorMaturity = Literal["experimental", "beta", "production"]
MAX_DISCOVERY_PAGE_SIZE = 100


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


FailureKind = Literal["transient", "rate_limited", "permanent"]


class ConnectorError(Exception):
    """Base exception for connector failures.

    Connector implementations may provide an explicit classification, but
    provider-facing errors normally only need to include their HTTP status or
    SDK message.  The shared classifier derives ``failure_kind`` and
    ``retryable`` once so callers (including durable jobs) cannot accidentally
    turn a provider failure into a successful empty discovery page.
    """

    failure_kind: FailureKind
    retryable: bool

    def __init__(
        self,
        message: str,
        *,
        failure_kind: FailureKind | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        inferred_kind, inferred_retryable = _classify_connector_message(str(self))
        self.failure_kind = failure_kind or inferred_kind
        if retryable is None:
            self.retryable = (
                inferred_retryable
                if failure_kind is None
                else failure_kind in {"transient", "rate_limited"}
            )
        else:
            self.retryable = retryable


def validate_discovered(seeds: object) -> list[Seed]:
    """Validate the provider-neutral discovery output contract.

    Connectors may use provider-specific pagination internally, but the
    collector boundary deliberately exposes a bounded list of typed seeds.
    Keeping this check at the boundary prevents malformed provider payloads
    from becoming person rows while preserving provider-specific seed source
    types (for example, Tavily's ``web`` and ``tavily_entity`` leads).
    """
    if not isinstance(seeds, list):
        raise ConnectorError("connector discovery output must be a list")
    if len(seeds) > MAX_DISCOVERY_PAGE_SIZE:
        raise ConnectorError(
            f"connector discovery page exceeds {MAX_DISCOVERY_PAGE_SIZE} seeds"
        )
    for index, seed in enumerate(seeds):
        if not isinstance(seed, Seed):
            raise ConnectorError(f"connector discovery seed {index} must be a Seed")
        if not isinstance(seed.source_type, str) or not seed.source_type.strip():
            raise ConnectorError(f"connector discovery seed {index} is missing source_type")
        if not isinstance(seed.handle, str) or not seed.handle.strip():
            raise ConnectorError(f"connector discovery seed {index} is missing handle")
        if not isinstance(seed.metadata, dict):
            raise ConnectorError(f"connector discovery seed {index} metadata must be an object")
    return seeds


def validate_collected(collected: Collected) -> None:
    """Validate the shared output contract before persistence or scoring."""
    if not isinstance(collected.content, bytes):
        raise ConnectorError("connector content must be bytes")
    if not collected.content:
        raise ConnectorError("connector returned empty content")
    if not isinstance(collected.content_type, str) or not collected.content_type.strip():
        raise ConnectorError("connector returned an empty content type")
    if not isinstance(collected.source_type, str) or not collected.source_type.strip():
        raise ConnectorError("connector returned an empty source type")
    if not isinstance(collected.uri, str) or not collected.uri.strip():
        raise ConnectorError("connector returned an empty source URI")
    if collected.license_hint is not None and not isinstance(collected.license_hint, dict):
        raise ConnectorError("connector license hint must be an object")
    if not isinstance(collected.observations, list):
        raise ConnectorError("connector observations must be a list")
    for observation in collected.observations:
        if not isinstance(observation, dict):
            raise ConnectorError("connector observations must be objects")
        predicate = observation.get("predicate")
        if not isinstance(predicate, str) or not predicate.strip():
            raise ConnectorError("connector observation is missing predicate")
        if "object_value" not in observation:
            raise ConnectorError("connector observation is missing object_value")
        object_value = observation["object_value"]
        if not isinstance(object_value, str):
            raise ConnectorError("connector observation object_value must be a string")
        if not object_value.strip():
            raise ConnectorError("connector observation has an empty object_value")
        raw_observed_at = observation.get("observed_at")
        if raw_observed_at is None or not str(raw_observed_at).strip():
            raise ConnectorError("connector observation is missing observed_at")
        if isinstance(raw_observed_at, datetime):
            continue
        if not isinstance(raw_observed_at, str):
            raise ConnectorError("connector observation has an invalid observed_at")
        try:
            datetime.fromisoformat(raw_observed_at)
        except ValueError as exc:
            raise ConnectorError("connector observation has an invalid observed_at") from exc


def classify_connector_failure(exc: BaseException) -> tuple[FailureKind, bool]:
    """Classify an upstream failure for retry and operator-facing state."""
    if isinstance(exc, ConnectorError):
        return exc.failure_kind, exc.retryable
    exception_name = type(exc).__name__.lower()
    if isinstance(exc, (TimeoutError, ConnectionError, BrokenPipeError)):
        return "transient", True
    if any(token in exception_name for token in ("ratelimit", "throttle")):
        return "rate_limited", True
    if isinstance(exc, OSError) and any(
        token in str(exc).lower()
        for token in ("network", "connection", "unreachable", "broken pipe")
    ):
        return "transient", True
    if any(
        token in exception_name
        for token in (
            "timeout",
            "connecterror",
            "networkerror",
            "readerror",
            "writeerror",
            "remoteprotocol",
            "protocolerror",
        )
    ):
        return "transient", True
    return _classify_connector_message(str(exc))


def _classify_connector_message(message: str) -> tuple[FailureKind, bool]:
    """Classify a provider message without requiring a provider SDK type."""
    message = message.lower()
    import re

    statuses = {
        int(match)
        for match in re.findall(
            r"(?:\bhttp(?:\s+status)?|\bstatus(?:_code)?|\bstatus)\s*[:=]?\s*(\d{3})\b",
            message,
        )
    }
    if any(
        (
            re.search(r"\b429\b", message) is not None,
            "rate limit" in message,
            "rate_limited" in message,
            "throttl" in message,
            "too many requests" in message,
        )
    ):
        return "rate_limited", True
    statuses.update(
        int(match)
        for match in re.findall(r"(?:error|code|response)\D+([45]\d{2})\b", message)
    )
    if any(500 <= status <= 599 for status in statuses):
        return "transient", True
    if any(status in {408, 425} for status in statuses):
        return "transient", True
    if any(400 <= status <= 499 for status in statuses):
        return "permanent", False
    if any(
        token in message
        for token in (
            "timeout",
            "timed out",
            "connection reset",
            "connection refused",
            "connection failed",
            "network error",
            "all connection attempts failed",
            "server disconnected",
            "disconnected without",
            "temporarily unavailable",
        )
    ):
        return "transient", True
    return "permanent", False


def normalize_connector_error(
    exc: BaseException,
    *,
    context: str = "connector_failure",
) -> ConnectorError:
    """Return a typed connector error while preserving an existing cause.

    This is intentionally provider-neutral: SDKs and HTTP clients differ in
    their exception classes, while jobs need one durable failure contract.
    """
    if isinstance(exc, ConnectorError):
        return exc
    failure_kind, retryable = classify_connector_failure(exc)
    detail = str(exc) or type(exc).__name__
    return ConnectorError(
        f"{context}: {detail}",
        failure_kind=failure_kind,
        retryable=retryable,
    )
