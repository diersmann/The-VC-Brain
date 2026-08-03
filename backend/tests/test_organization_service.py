"""Tests for deterministic organization identity helpers."""

from app.opportunity_service import organization_stable_id


def test_organization_stable_id_is_case_and_whitespace_insensitive() -> None:
    assert organization_stable_id("  Example   Labs ") == organization_stable_id(
        "example labs"
    )


def test_organization_stable_id_has_non_name_key() -> None:
    assert organization_stable_id("Example Labs").startswith("company:")
    assert "Example Labs" not in organization_stable_id("Example Labs")
