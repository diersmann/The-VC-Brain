"""Database-facing fingerprints for immutable collector persistence.

These fingerprints are deduplication keys, not security hashes. Values use a
length-prefixed UTF-8 encoding so arbitrary predicate/object/URI text cannot
create delimiter collisions; the content hash, extractor version, and optional
source locator remain part of the key so a changed source, extractor, or page
coordinate can append a new observation.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _fingerprint(parts: tuple[Any, ...]) -> str:
    payload = bytearray()
    for part in parts:
        value = "" if part is None else str(part)
        encoded = value.encode("utf-8")
        payload.extend(str(len(encoded)).encode("ascii"))
        payload.extend(b":")
        payload.extend(encoded)
    return hashlib.md5(bytes(payload), usedforsecurity=False).hexdigest()


def snapshot_persistence_fingerprint(uri: str, source_type: str, content_hash: str) -> str:
    """Return the stable key for one immutable source snapshot version."""
    return _fingerprint((uri, source_type, content_hash))


def observation_persistence_fingerprint(
    *,
    snapshot_id: Any,
    subject_id: Any,
    opportunity_id: Any,
    predicate: str,
    object_value: str,
    extractor_version: str,
    source_locator: object | None = None,
) -> str:
    """Return the stable key for one observation extraction output."""
    normalized_locator = (
        json.dumps(source_locator, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if source_locator is not None
        else ""
    )
    return _fingerprint(
        (
            snapshot_id,
            subject_id,
            opportunity_id,
            predicate,
            object_value,
            extractor_version,
            normalized_locator,
        )
    )
