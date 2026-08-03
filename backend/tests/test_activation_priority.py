"""Tests for the versioned activation-priority contract."""

from app.activation_priority import ACTIVATION_PRIORITY_VERSION, compute_activation_priority
from app.collectors.priority import priority


def test_activation_priority_records_missing_inputs_without_penalizing_known_quality() -> None:
    result = compute_activation_priority(
        thesis_fit=0.8,
        novelty=None,
        momentum=None,
        evidence_confidence=0.9,
        identity_confidence=None,
        contactability=None,
        deadline_pressure=0.2,
        cost=1.0,
        exploration_quota=None,
    )

    assert result.version == ACTIVATION_PRIORITY_VERSION
    assert 0.0 < result.score <= 1.0
    assert "novelty" in result.missing
    assert "identity_confidence" in result.missing
    assert "missing:" in result.rationale


def test_complete_activation_priority_is_bounded_and_used_for_queue_priority() -> None:
    result = compute_activation_priority(
        thesis_fit=1.0,
        novelty=1.0,
        momentum=1.0,
        evidence_confidence=1.0,
        identity_confidence=1.0,
        contactability=1.0,
        deadline_pressure=1.0,
        cost=0.0,
        exploration_quota=1.0,
    )

    assert result.score == 1.0
    assert result.missing == ()
    assert priority(
        info_gain=0.5,
        cost=0.0,
        authority=1.0,
        thesis_fit=1.0,
        novelty=1.0,
        momentum=1.0,
        evidence_confidence=1.0,
        identity_confidence=1.0,
        contactability=1.0,
        deadline_pressure=1.0,
        exploration_quota=1.0,
    ) == 10.0
