"""Single source of truth for deal lifecycle stages and transitions.

Per the architecture doc (§Unified Deal Lifecycle), outbound and inbound
opportunities converge into one pipeline::

    Outbound: discovered -> interesting -> investigating -> contacted -> received
    Inbound:                                                       -> received
    Shared:   received -> memo_ready -> approved | closed

All transitions are auto-driven by ``advance_pipeline_job`` except
``memo_ready -> approved | closed`` which requires a human decision.
"""

from __future__ import annotations

STAGES = [
    "discovered",
    "interesting",
    "investigating",
    "contacted",
    "received",
    "memo_ready",
    "hold",
    "approved",
    "closed",
]

# Legacy states kept for backwards compatibility (existing inbound data).
LEGACY_STAGES = ["screening", "triage", "diligence"]

# Valid forward transitions.  A transition not listed here is invalid.
TRANSITIONS: dict[str, tuple[str, ...]] = {
    "discovered": ("interesting", "closed"),
    "interesting": ("investigating", "closed"),
    "investigating": ("contacted", "received", "closed"),
    "contacted": ("received", "closed"),
    "received": ("memo_ready", "closed"),
    "memo_ready": ("hold", "approved", "closed"),
    "hold": ("approved", "closed"),
    "approved": (),
    "closed": (),
    # Legacy states map onto the new pipeline:
    "screening": ("diligence", "memo_ready", "closed"),
    "triage": ("screening", "closed"),
    "diligence": ("memo_ready", "closed"),
}

_OUTBOUND_STAGES = {"discovered", "interesting", "investigating", "contacted"}
_INBOUND_STAGES = {"received", "memo_ready", "hold", "approved", "closed"}


def is_valid_transition(prior: str, new: str) -> bool:
    """Return True if *prior -> new* is an allowed forward transition."""
    if prior == new:
        return True  # idempotent
    return new in TRANSITIONS.get(prior, ())


def is_outbound(stage: str) -> bool:
    """Return True if *stage* is an outbound-only stage."""
    return stage in _OUTBOUND_STAGES


def is_inbound(stage: str) -> bool:
    """Return True if *stage* is a shared post-inbound stage."""
    return stage in _INBOUND_STAGES


def is_memo_ready(status: str) -> bool:
    """Return whether a memo has passed generation validation."""
    return status == "succeeded"


def advance_reason(prior: str, new: str, *, detail: str = "") -> str:
    """Generate a human-readable reason for a DecisionEvent."""
    label_map = {
        "interesting": "Signal crossed interesting threshold",
        "investigating": "Investigation started (research + scoring + processing)",
        "contacted": "Cold outreach confirmed by provider",
        "received": "Inbound application received",
        "memo_ready": "Investment memo generated",
        "approved": "Investment approved",
        "closed": "Opportunity closed",
    }
    base = label_map.get(new, new)
    if detail:
        return f"{base} — {detail}"
    return base
