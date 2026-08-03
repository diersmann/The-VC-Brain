"""Versioned activation-priority model for sourcing and pipeline work."""

from __future__ import annotations

from dataclasses import dataclass

ACTIVATION_PRIORITY_VERSION = "activation-priority-v1"

_WEIGHTS: dict[str, float] = {
    "thesis_fit": 0.18,
    "novelty": 0.12,
    "momentum": 0.10,
    "evidence_confidence": 0.14,
    "identity_confidence": 0.12,
    "contactability": 0.10,
    "deadline_pressure": 0.10,
    "cost_efficiency": 0.08,
    "exploration_quota": 0.06,
}


@dataclass(frozen=True)
class ActivationPriority:
    """A bounded, explainable activation score and its evidence coverage."""

    version: str
    score: float
    components: dict[str, float | None]
    missing: tuple[str, ...]
    rationale: str


def _bounded(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))


def compute_activation_priority(
    *,
    thesis_fit: float | None,
    novelty: float | None,
    momentum: float | None,
    evidence_confidence: float | None,
    identity_confidence: float | None,
    contactability: float | None,
    deadline_pressure: float | None,
    cost: float | None,
    exploration_quota: float | None,
) -> ActivationPriority:
    """Score activation urgency while renormalizing over known inputs.

    Missing values are excluded from the weighted average and listed in the
    rationale. They never become a negative founder-quality signal.
    """
    components: dict[str, float | None] = {
        "thesis_fit": _bounded(thesis_fit),
        "novelty": _bounded(novelty),
        "momentum": _bounded(momentum),
        "evidence_confidence": _bounded(evidence_confidence),
        "identity_confidence": _bounded(identity_confidence),
        "contactability": _bounded(contactability),
        "deadline_pressure": _bounded(deadline_pressure),
        "cost_efficiency": None if cost is None else 1.0 / (1.0 + max(0.0, float(cost))),
        "exploration_quota": _bounded(exploration_quota),
    }
    known = {key: value for key, value in components.items() if value is not None}
    weight = sum(_WEIGHTS[key] for key in known)
    score = (
        sum(float(value) * _WEIGHTS[key] for key, value in known.items()) / weight
        if weight
        else 0.0
    )
    missing = tuple(key for key in _WEIGHTS if key not in known)
    if missing:
        rationale = f"Known activation signals were renormalized; missing: {', '.join(missing)}."
    else:
        rationale = "All activation signals are present and weighted by activation-priority-v1."
    return ActivationPriority(
        version=ACTIVATION_PRIORITY_VERSION,
        score=round(score, 4),
        components=components,
        missing=missing,
        rationale=rationale,
    )
