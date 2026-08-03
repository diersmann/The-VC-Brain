"""Versioned canonical deal lifecycle contract.

The state machine is shared by transition validation, worker orchestration,
API status normalization, and the frontend workflow diagram. Opportunity
creation timestamps establish the initial state; DecisionEvent timestamps are
authoritative for subsequent state transitions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

LIFECYCLE_CONTRACT_VERSION = "unified-v2"
_EVENT_TIMESTAMP_SOURCE = (
    "Opportunity.created_at for initial entry; DecisionEvent.created_at for transitions"
)


@dataclass(frozen=True)
class LifecycleDefinition:
    key: str
    label: str
    lane: str
    entry_requirements: tuple[str, ...]
    exit_requirements: tuple[str, ...]
    actors: tuple[str, ...]
    transitions: tuple[str, ...]


_DEFINITIONS: tuple[LifecycleDefinition, ...] = (
    LifecycleDefinition(
        "discovered",
        "Discovered",
        "outbound",
        ("Canonical person identity exists", "At least one source signal is stored"),
        ("Signal composite crosses the configured threshold",),
        ("pipeline:auto",),
        ("interesting", "closed"),
    ),
    LifecycleDefinition(
        "interesting",
        "Interesting",
        "outbound",
        ("Signal threshold has been crossed",),
        ("Investigation budget is available",),
        ("pipeline:auto",),
        ("investigating", "closed"),
    ),
    LifecycleDefinition(
        "investigating",
        "Investigating",
        "outbound",
        ("Opportunity is linked to a canonical founder",),
        ("Research, Founder Score, and processing jobs are queued",),
        ("pipeline:auto",),
        ("contacted", "received", "closed"),
    ),
    LifecycleDefinition(
        "contacted",
        "Contacted",
        "outbound",
        ("A reviewable outreach draft exists",),
        ("Provider-confirmed contact or founder submission exists",),
        ("pipeline:auto", "human"),
        ("received", "closed"),
    ),
    LifecycleDefinition(
        "received",
        "Received",
        "inbound",
        ("Validated inbound submission or confirmed founder response exists",),
        ("Scoped processing claims exist",),
        ("pipeline:auto",),
        ("triage", "closed"),
    ),
    LifecycleDefinition(
        "triage",
        "Triage",
        "inbound",
        ("Received opportunity has scoped accepted claims",),
        ("Person-level Founder Score exists",),
        ("pipeline:auto",),
        ("screening", "closed"),
    ),
    LifecycleDefinition(
        "screening",
        "Screening",
        "inbound",
        ("Triage output and Founder Score exist",),
        ("Founder, Market, and Idea-Market assessments exist",),
        ("pipeline:auto",),
        ("diligence", "closed"),
    ),
    LifecycleDefinition(
        "diligence",
        "Diligence",
        "inbound",
        ("Three opportunity axes are persisted",),
        ("A validated succeeded memo exists",),
        ("pipeline:auto", "human"),
        ("memo_ready", "closed"),
    ),
    LifecycleDefinition(
        "memo_ready",
        "Memo ready",
        "decision",
        ("Validated succeeded memo exists",),
        ("Human decision is recorded with a reason",),
        ("pipeline:auto", "human"),
        ("hold", "approved", "closed"),
    ),
    LifecycleDefinition(
        "hold",
        "On hold",
        "decision",
        ("Human hold decision includes a reason",),
        ("Human resumes or closes the opportunity",),
        ("human",),
        ("approved", "closed"),
    ),
    LifecycleDefinition(
        "approved",
        "Approved",
        "terminal",
        ("Human proceed decision references the memo and evidence",),
        (),
        ("human",),
        (),
    ),
    LifecycleDefinition(
        "closed",
        "Closed",
        "terminal",
        ("Human decline or explicit system timeout has a reason",),
        (),
        ("human", "pipeline:auto"),
        (),
    ),
)

STAGES = [definition.key for definition in _DEFINITIONS]
TRANSITIONS: dict[str, tuple[str, ...]] = {
    definition.key: definition.transitions for definition in _DEFINITIONS
}
LEGACY_STAGES: list[str] = []

_OUTBOUND_STAGES = {definition.key for definition in _DEFINITIONS if definition.lane == "outbound"}
_INBOUND_STAGES = {
    definition.key
    for definition in _DEFINITIONS
    if definition.lane in {"inbound", "decision", "terminal"}
}


def definitions() -> tuple[LifecycleDefinition, ...]:
    """Return immutable stage definitions for internal consumers."""
    return _DEFINITIONS


def lifecycle_contract() -> dict[str, object]:
    """Return the JSON-safe contract consumed by the API and UI."""
    stages: list[dict[str, object]] = []
    for definition in _DEFINITIONS:
        item = asdict(definition)
        item["entry_requirements"] = list(definition.entry_requirements)
        item["exit_requirements"] = list(definition.exit_requirements)
        item["actors"] = list(definition.actors)
        item["transitions"] = list(definition.transitions)
        item["timestamp_source"] = _EVENT_TIMESTAMP_SOURCE
        stages.append(item)
    return {"version": LIFECYCLE_CONTRACT_VERSION, "stages": stages}


def is_valid_transition(prior: str, new: str) -> bool:
    """Return True if *prior -> new* is an allowed forward transition."""
    if prior == new:
        return True
    return new in TRANSITIONS.get(prior, ())


def is_outbound(stage: str) -> bool:
    """Return whether a stage belongs to outbound sourcing."""
    return stage in _OUTBOUND_STAGES


def is_inbound(stage: str) -> bool:
    """Return whether a stage belongs to the shared inbound decision flow."""
    return stage in _INBOUND_STAGES


def is_memo_ready(status: str) -> bool:
    """Return whether a memo has passed generation validation."""
    return status == "succeeded"


def advance_reason(prior: str, new: str, *, detail: str = "") -> str:
    """Generate an auditable human-readable reason for a transition."""
    reason_labels = {
        "interesting": "Signal crossed interesting threshold",
        "investigating": "Investigation started",
        "contacted": "Outreach contact stage",
        "received": "Inbound application received",
        "memo_ready": "Investment memo generated",
        "approved": "Investment approved",
        "closed": "Opportunity closed",
    }
    labels = {definition.key: definition.label for definition in _DEFINITIONS}
    base = reason_labels.get(new, labels.get(new, new))
    if detail:
        return f"{base} — {detail}"
    return base
