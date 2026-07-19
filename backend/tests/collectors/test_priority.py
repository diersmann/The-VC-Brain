"""Tests for collection priority math."""

from app.collectors.priority import info_gain, priority


def test_info_gain_low_signal_high_gain() -> None:
    """Low signal score should produce higher information gain."""
    gain = info_gain(signal_score=0.1, staleness_days=0.0)
    assert 0.4 < gain < 0.7, f"Expected moderate gain for low signal, got {gain}"


def test_info_gain_high_signal_low_gain() -> None:
    """High signal score should produce lower information gain."""
    gain = info_gain(signal_score=0.9, staleness_days=0.0)
    assert gain < 0.5, f"Expected low gain for high signal, got {gain}"


def test_info_gain_staleness_increases_gain() -> None:
    """Older data should increase information gain."""
    fresh = info_gain(signal_score=0.5, staleness_days=0.0)
    stale = info_gain(signal_score=0.5, staleness_days=90.0)
    assert stale > fresh, "Stale data should have higher gain"


def test_info_gain_deadline_pressure() -> None:
    """Deadline pressure should increase information gain."""
    no_deadline = info_gain(signal_score=0.5, staleness_days=0.0, deadline_pressure=0.0)
    urgent = info_gain(signal_score=0.5, staleness_days=0.0, deadline_pressure=1.0)
    assert urgent > no_deadline, "Urgent tasks should have higher gain"


def test_priority_cheaper_is_higher() -> None:
    """Lower cost should produce higher priority (all else equal)."""
    cheap = priority(info_gain=0.5, cost=1.0, authority=0.5)
    expensive = priority(info_gain=0.5, cost=5.0, authority=0.5)
    assert cheap > expensive, "Cheaper tasks should have higher priority"


def test_priority_higher_authority_amplifies() -> None:
    """Higher authority should amplify priority."""
    low_auth = priority(info_gain=0.5, cost=1.0, authority=0.2)
    high_auth = priority(info_gain=0.5, cost=1.0, authority=0.9)
    assert high_auth > low_auth, "Higher authority should amplify priority"


def test_priority_zero_cost_does_not_divide_by_zero() -> None:
    """Zero cost should be clamped to a small positive value."""
    p = priority(info_gain=0.5, cost=0.0, authority=0.5)
    assert p > 0, "Priority should be positive even with zero cost"
