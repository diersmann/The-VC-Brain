"""Tests for outcome separation and provenance requirements."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.opportunity_service import record_opportunity_outcome


class _Session:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, instance: object) -> None:
        self.added.append(instance)


def test_outcome_record_keeps_decision_selection_separate_from_longitudinal_value() -> None:
    session = _Session()

    outcome = record_opportunity_outcome(
        session,
        uuid.uuid4(),
        outcome_domain="decision",
        outcome_type="investor_decision",
        source_type="decision_event",
        source_ref="event:123",
        observed_at=datetime(2026, 8, 3, tzinfo=UTC),
        outcome_value={"action": "decline"},
        horizon_days=0,
        provenance={"actor": "human", "selection_signal_only": True},
    )

    assert session.added == [outcome]
    assert outcome.outcome_domain == "decision"
    assert outcome.outcome_value == {"action": "decline"}
    assert outcome.provenance["selection_signal_only"] is True


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"outcome_domain": "merit", "outcome_type": "success"}, "unsupported outcome"),
        (
            {"outcome_domain": "process", "outcome_type": "reply", "horizon_days": -1},
            "non-negative",
        ),
        (
            {"outcome_domain": "process", "outcome_type": "reply", "confidence": 1.1},
            "between 0 and 1",
        ),
    ],
)
def test_outcome_record_rejects_ambiguous_or_invalid_values(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        record_opportunity_outcome(
            _Session(),
            uuid.uuid4(),
            source_type="test",
            observed_at=datetime(2026, 8, 3, tzinfo=UTC),
            **kwargs,
        )
