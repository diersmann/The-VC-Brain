"""Deterministic construction of versioned decision proposals."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

DECISION_PROPOSAL_VERSION = "decision-proposal-v1"
_AXES = ("Founder", "Market", "Idea-Market")


def build_decision_proposal(
    *,
    assessments: Iterable[Any],
    claim_ids: Sequence[str],
    thesis_version: str | None,
    memo_status: str,
    memo_model_version: str | None,
    rubric_versions: Sequence[str] = (),
    action: str | None = None,
    override_reason: str | None = None,
    status: str = "draft",
) -> dict[str, Any]:
    """Build a JSON-safe proposal and readiness snapshot from persisted inputs."""
    by_axis: dict[str, Any] = {}
    for assessment in assessments:
        axis = str(getattr(assessment, "axis", ""))
        canonical = next((item for item in _AXES if item.casefold() == axis.casefold()), None)
        if canonical is not None and canonical not in by_axis:
            by_axis[canonical] = assessment

    readiness_blockers = [
        f"missing_{axis.casefold().replace('-', '_')}_assessment"
        for axis in _AXES
        if axis not in by_axis
    ]
    if memo_status != "succeeded":
        readiness_blockers.append("memo_not_validated")

    ratings = [str(getattr(item, "rating", "")).casefold() for item in by_axis.values()]
    if action is None:
        if "bearish" in ratings:
            action = "hold"
        elif len(ratings) == len(_AXES) and all(rating == "bullish" for rating in ratings):
            action = "invest"
        else:
            action = "investigate"

    confidences = [float(getattr(item, "confidence", 0.0)) for item in by_axis.values()]
    average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    if not confidences:
        conviction = None
    elif average_confidence >= 0.75 and action == "invest":
        conviction = "high"
    elif average_confidence >= 0.55:
        conviction = "medium"
    else:
        conviction = "low"

    top_risks: list[str] = []
    for axis in _AXES:
        assessment = by_axis.get(axis)
        if assessment is None:
            continue
        if str(getattr(assessment, "rating", "")).casefold() == "bearish":
            top_risks.append(f"{axis} assessment is Bearish")
        for unknown in getattr(assessment, "unknowns", []) or []:
            if str(unknown) not in top_risks:
                top_risks.append(str(unknown))

    open_conditions = [f"Resolve: {risk}" for risk in top_risks]
    versions = list(dict.fromkeys([*rubric_versions, DECISION_PROPOSAL_VERSION]))
    assessment_ids = {
        f"{axis.casefold().replace('-', '_')}_assessment_id": (
            str(by_axis[axis].id) if axis in by_axis else None
        )
        for axis in _AXES
    }
    return {
        "action": action,
        "check_amount": None,
        "ownership_target": None,
        "conviction": conviction,
        **assessment_ids,
        "top_evidence": list(dict.fromkeys(str(item) for item in claim_ids))[:8],
        "top_risks": top_risks[:8],
        "open_conditions": open_conditions[:8],
        "readiness_blockers": readiness_blockers,
        "readiness_status": "ready" if not readiness_blockers else "blocked",
        "thesis_version": thesis_version,
        "rubric_versions": versions,
        "memo_model_version": memo_model_version,
        "override_reason": override_reason,
        "status": status,
    }
