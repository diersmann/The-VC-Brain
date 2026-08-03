"""Tests for the persisted 24-hour decision clock."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.opportunity_service import transition_opportunity
from app.sla import (
    SLA_TOTAL_BUDGET,
    build_stage_deadlines,
    evaluate_sla,
    finalize_sla,
    initialize_sla,
)

START = datetime(2026, 8, 3, 10, 0, tzinfo=UTC)


def _opportunity() -> SimpleNamespace:
    return SimpleNamespace(
        lifecycle_state="received",
        received_at=None,
        decision_due_at=None,
        stage_deadlines={},
        sla_owner=None,
        sla_pause_reason=None,
        sla_attainment="pending",
        sla_decided_at=None,
    )


def test_stage_deadlines_sum_to_the_24_hour_decision_budget() -> None:
    deadlines = build_stage_deadlines(START)

    assert set(deadlines) == {"triage", "screening", "diligence", "memo", "human_decision"}
    assert datetime.fromisoformat(deadlines["human_decision"]) == START + SLA_TOTAL_BUDGET


def test_initialize_sla_is_idempotent_and_preserves_start_time() -> None:
    opportunity = _opportunity()

    initialize_sla(opportunity, START)
    first_due = opportunity.decision_due_at
    initialize_sla(opportunity, START + timedelta(hours=2))

    assert opportunity.received_at == START
    assert opportunity.decision_due_at == first_due
    assert opportunity.sla_attainment == "pending"


def test_evaluate_sla_exposes_stage_countdown_and_warning() -> None:
    opportunity = _opportunity()
    initialize_sla(opportunity, START)

    status = evaluate_sla(
        lifecycle_state=opportunity.lifecycle_state,
        received_at=opportunity.received_at,
        decision_due_at=opportunity.decision_due_at,
        stage_deadlines=opportunity.stage_deadlines,
        sla_owner=opportunity.sla_owner,
        sla_pause_reason=opportunity.sla_pause_reason,
        sla_attainment=opportunity.sla_attainment,
        now=START + timedelta(hours=22, minutes=30),
    )

    assert status["stage"] == "triage"
    assert status["status"] == "at_risk"
    assert status["alert"] is True
    assert status["remaining_seconds"] == 5400


def test_evaluate_sla_marks_expired_clock_as_breached() -> None:
    opportunity = _opportunity()
    initialize_sla(opportunity, START)

    status = evaluate_sla(
        lifecycle_state=opportunity.lifecycle_state,
        received_at=opportunity.received_at,
        decision_due_at=opportunity.decision_due_at,
        stage_deadlines=opportunity.stage_deadlines,
        sla_owner=opportunity.sla_owner,
        sla_pause_reason=opportunity.sla_pause_reason,
        sla_attainment=opportunity.sla_attainment,
        now=START + timedelta(hours=24, seconds=1),
    )

    assert status["status"] == "breached"
    assert status["alert_level"] == "breach"


def test_finalize_sla_persists_decision_attainment() -> None:
    opportunity = _opportunity()
    initialize_sla(opportunity, START)

    status = finalize_sla(opportunity, START + timedelta(hours=23))

    assert opportunity.sla_attainment == "met"
    assert opportunity.sla_decided_at == START + timedelta(hours=23)
    assert status["status"] == "met"


@pytest.mark.asyncio
async def test_idempotent_received_transition_repairs_missing_clock() -> None:
    opportunity = _opportunity()
    opportunity.id = "opportunity-1"

    event = await transition_opportunity(AsyncMock(), opportunity, "received")

    assert event.reason.startswith("(no-op)")
    assert opportunity.received_at is not None
    assert opportunity.decision_due_at is not None
    assert opportunity.stage_deadlines
