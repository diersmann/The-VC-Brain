"""Versioned source-use policy for collection, model, contact, and export."""

from __future__ import annotations

from typing import Any

SOURCE_POLICY_VERSION = "source-use-v1"


def build_source_use_policy(
    source_type: str, license_metadata: dict[str, object] | None
) -> dict[str, object]:
    """Compile license metadata into an explicit, deny-by-default use policy."""
    policy: dict[str, object] = {
        "version": SOURCE_POLICY_VERSION,
        "source_type": source_type,
        "status": "unknown",
        "collection": "review",
        "retention": "review",
        "display": "denied",
        "model_use": "denied",
        "contact": "denied",
        "export": "denied",
    }
    if source_type in {"inbound_deck", "outreach"}:
        policy.update(
            {
                "status": "allowed",
                "collection": "allowed",
                "retention": "allowed",
                "display": "allowed",
                "model_use": "allowed",
                "contact": "allowed" if source_type == "outreach" else "denied",
            }
        )
    if license_metadata and license_metadata.get("model_use") == "allowed":
        policy.update(
            {
                "status": "allowed",
                "collection": "allowed",
                "retention": "allowed",
                "model_use": "allowed",
            }
        )
    if license_metadata:
        policy["license_metadata"] = license_metadata
    return policy


def source_allows_model_use(snapshot: Any) -> bool:
    """Return whether a snapshot is allowed to enter an AI/model input package."""
    policy = getattr(snapshot, "source_use_policy", None)
    return isinstance(policy, dict) and policy.get("model_use") == "allowed"
