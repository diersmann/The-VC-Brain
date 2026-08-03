"""Deterministic 24-hour inbound decision SLA calculations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

SLA_STAGE_BUDGETS: dict[str, timedelta] = {
    "triage": timedelta(minutes=30),
    "screening": timedelta(hours=3),
    "diligence": timedelta(hours=14),
    "memo": timedelta(hours=4),
    "human_decision": timedelta(hours=2, minutes=30),
}
SLA_STAGE_ORDER = tuple(SLA_STAGE_BUDGETS)
SLA_TOTAL_BUDGET = sum(SLA_STAGE_BUDGETS.values(), timedelta())
_AT_RISK_WINDOW = timedelta(hours=2)


def _as_utc(value: datetime) -> datetime:
    """Normalize a datetime for stable arithmetic and JSON output."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso(value: datetime) -> str:
    return _as_utc(value).isoformat()


def build_stage_deadlines(received_at: datetime) -> dict[str, str]:
    """Return absolute UTC deadlines for the architecture's stage budgets."""
    cursor = _as_utc(received_at)
    deadlines: dict[str, str] = {}
    for stage, budget in SLA_STAGE_BUDGETS.items():
        cursor += budget
        deadlines[stage] = _iso(cursor)
    return deadlines


def initialize_sla(opportunity: Any, received_at: datetime | None = None) -> None:
    """Start the decision clock once, preserving an existing start time."""
    started = received_at or datetime.now(UTC)
    if getattr(opportunity, "received_at", None) is not None:
        return
    started = _as_utc(started)
    opportunity.received_at = started
    opportunity.decision_due_at = started + SLA_TOTAL_BUDGET
    opportunity.stage_deadlines = build_stage_deadlines(started)
    opportunity.sla_attainment = "pending"


def _parse_deadline(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return _as_utc(value)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str):
        try:
            return _as_utc(datetime.fromisoformat(value))
        except ValueError:
            return None
    return None


def current_stage(lifecycle_state: str | None) -> str | None:
    """Map current domain state to the SLA stage without inventing states."""
    if lifecycle_state is None:
        return None
    return {
        "received": "triage",
        "triage": "triage",
        "screening": "screening",
        "diligence": "diligence",
        "memo_ready": "human_decision",
        "hold": "human_decision",
        "approved": "human_decision",
        "closed": "human_decision",
    }.get(lifecycle_state)


def evaluate_sla(
    *,
    lifecycle_state: str | None,
    received_at: datetime | None,
    decision_due_at: datetime | None,
    stage_deadlines: dict[str, object] | None,
    sla_owner: str | None,
    sla_pause_reason: str | None,
    sla_attainment: str | None,
    now: datetime | None = None,
) -> dict[str, object]:
    """Return the current SLA state from persisted timestamps and events."""
    if received_at is None or decision_due_at is None:
        return {
            "received_at": None,
            "decision_due_at": None,
            "stage_deadlines": {},
            "owner": sla_owner,
            "pause_reason": sla_pause_reason,
            "stage": None,
            "status": "not_started",
            "attainment": sla_attainment or "pending",
            "remaining_seconds": None,
            "stage_remaining_seconds": None,
            "elapsed_seconds": None,
            "alert": False,
            "alert_level": "none",
        }

    current = _as_utc(now or datetime.now(UTC))
    received = _as_utc(received_at)
    due = _as_utc(decision_due_at)
    stage = current_stage(lifecycle_state)
    parsed_deadlines = {
        name: deadline
        for name, raw in (stage_deadlines or {}).items()
        if (deadline := _parse_deadline(raw)) is not None
    }
    remaining = int((due - current).total_seconds())
    stage_due: datetime | None = None
    if stage is not None:
        stage_due = parsed_deadlines.get(stage)
    stage_remaining = (
        int((stage_due - current).total_seconds()) if stage_due is not None else None
    )

    if sla_pause_reason:
        status = "paused"
        alert_level = "paused"
    elif sla_attainment in {"met", "breached"}:
        status = sla_attainment
        alert_level = "none" if status == "met" else "breach"
    elif remaining <= 0:
        status = "breached"
        alert_level = "breach"
    elif remaining <= _AT_RISK_WINDOW.total_seconds():
        status = "at_risk"
        alert_level = "warning"
    else:
        status = "on_track"
        alert_level = "none"

    return {
        "received_at": received,
        "decision_due_at": due,
        "stage_deadlines": parsed_deadlines,
        "owner": sla_owner,
        "pause_reason": sla_pause_reason,
        "stage": stage,
        "status": status,
        "attainment": sla_attainment or "pending",
        "remaining_seconds": remaining,
        "stage_remaining_seconds": stage_remaining,
        "elapsed_seconds": max(0, int((current - received).total_seconds())),
        "alert": status in {"at_risk", "breached"},
        "alert_level": alert_level,
    }


def finalize_sla(opportunity: Any, decided_at: datetime | None = None) -> dict[str, object]:
    """Persist SLA attainment when a human decision event is recorded."""
    if getattr(opportunity, "received_at", None) is None:
        return evaluate_sla(
            lifecycle_state=getattr(opportunity, "lifecycle_state", None),
            received_at=None,
            decision_due_at=None,
            stage_deadlines=None,
            sla_owner=getattr(opportunity, "sla_owner", None),
            sla_pause_reason=getattr(opportunity, "sla_pause_reason", None),
            sla_attainment=getattr(opportunity, "sla_attainment", None),
            now=decided_at,
        )

    decided = _as_utc(decided_at or datetime.now(UTC))
    due = getattr(opportunity, "decision_due_at", None)
    attainment = "met" if due is not None and decided <= _as_utc(due) else "breached"
    opportunity.sla_attainment = attainment
    opportunity.sla_decided_at = decided
    return evaluate_sla(
        lifecycle_state=getattr(opportunity, "lifecycle_state", None),
        received_at=opportunity.received_at,
        decision_due_at=due,
        stage_deadlines=getattr(opportunity, "stage_deadlines", None),
        sla_owner=getattr(opportunity, "sla_owner", None),
        sla_pause_reason=getattr(opportunity, "sla_pause_reason", None),
        sla_attainment=attainment,
        now=decided,
    )
