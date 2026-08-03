"""Shared provenance contract for derived artifacts and model invocations."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

ARTIFACT_PROVENANCE_VERSION = "artifact-provenance-v1"


def fingerprint_payload(payload: Any) -> str:
    """Return a stable SHA-256 fingerprint for an artifact input package."""
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_artifact_metadata(
    *,
    run_id: uuid.UUID,
    artifact_type: str,
    code_version: str,
    input_fingerprint: str,
    rubric_versions: Sequence[str] = (),
    prompt_version: str | None = None,
    model_version: str | None = None,
    parameters: Mapping[str, Any] | None = None,
    latency_ms: int | None = None,
    cost_usd: float | None = None,
    validator_status: str = "not_applicable",
    validator_errors: Sequence[str] = (),
    compatibility: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    """Build JSON-safe metadata with explicit unknown and compatibility values."""
    return {
        "contract_version": ARTIFACT_PROVENANCE_VERSION,
        "artifact_type": artifact_type,
        "run_id": str(run_id),
        "code_version": code_version,
        "rubric_versions": list(rubric_versions),
        "prompt_version": prompt_version,
        "model_version": model_version,
        "parameters": dict(parameters or {}),
        "input_fingerprint": input_fingerprint,
        "latency_ms": latency_ms,
        "cost_usd": cost_usd,
        "validator_status": validator_status,
        "validator_errors": list(validator_errors),
        "compatibility": dict(compatibility or {"reader": ARTIFACT_PROVENANCE_VERSION}),
    }
