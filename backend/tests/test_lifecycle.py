"""Tests for lifecycle stage model."""

from app.lifecycle import (
    STAGES,
    TRANSITIONS,
    advance_reason,
    is_inbound,
    is_outbound,
    is_valid_transition,
)


def test_all_stages_defined() -> None:
    """Every stage in STAGES should have a TRANSITIONS entry."""
    for stage in STAGES:
        assert stage in TRANSITIONS, f"Missing transition for {stage}"


def test_valid_transitions() -> None:
    """Known valid transitions should return True."""
    assert is_valid_transition("discovered", "interesting") is True
    assert is_valid_transition("interesting", "investigating") is True
    assert is_valid_transition("investigating", "contacted") is True
    assert is_valid_transition("contacted", "received") is True
    assert is_valid_transition("received", "memo_ready") is True
    assert is_valid_transition("memo_ready", "approved") is True
    assert is_valid_transition("memo_ready", "hold") is True
    assert is_valid_transition("hold", "approved") is True
    assert is_valid_transition("memo_ready", "closed") is True
    assert is_valid_transition("investigating", "received") is True
    assert is_valid_transition("investigating", "closed") is True


def test_invalid_transitions() -> None:
    """Invalid transitions should return False."""
    assert is_valid_transition("discovered", "memo_ready") is False
    assert is_valid_transition("interesting", "approved") is False
    assert is_valid_transition("contacted", "memo_ready") is False
    assert is_valid_transition("memo_ready", "investigating") is False
    assert is_valid_transition("approved", "memo_ready") is False


def test_idempotent_transition() -> None:
    """Same state should always be valid (idempotent)."""
    for stage in STAGES:
        assert is_valid_transition(stage, stage) is True


def test_is_outbound() -> None:
    """Outbound stages should be classified correctly."""
    assert is_outbound("discovered") is True
    assert is_outbound("interesting") is True
    assert is_outbound("investigating") is True
    assert is_outbound("contacted") is True
    assert is_outbound("received") is False
    assert is_outbound("memo_ready") is False
    assert is_outbound("approved") is False
    assert is_outbound("closed") is False


def test_is_inbound() -> None:
    """Inbound stages should be classified correctly."""
    assert is_inbound("received") is True
    assert is_inbound("memo_ready") is True
    assert is_inbound("approved") is True
    assert is_inbound("hold") is True
    assert is_inbound("closed") is True
    assert is_inbound("discovered") is False
    assert is_inbound("interesting") is False
    assert is_inbound("investigating") is False
    assert is_inbound("contacted") is False


def test_advance_reason() -> None:
    """advance_reason should produce a human-readable string."""
    reason = advance_reason("discovered", "interesting")
    assert "interesting" in reason.lower()
    assert "Signal" in reason

    reason = advance_reason("investigating", "contacted", detail="composite 0.72")
    assert "composite 0.72" in reason


def test_legacy_stages() -> None:
    """Legacy stages (screening, triage, diligence) should have valid transitions."""
    assert is_valid_transition("screening", "diligence") is True
    assert is_valid_transition("screening", "memo_ready") is True
    assert is_valid_transition("screening", "closed") is True
    assert is_valid_transition("triage", "screening") is True
    assert is_valid_transition("triage", "closed") is True
    assert is_valid_transition("diligence", "memo_ready") is True
    assert is_valid_transition("diligence", "closed") is True
