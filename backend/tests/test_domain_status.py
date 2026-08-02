import pytest

from app.domain_status import (
    normalize_assessment_axis,
    normalize_assessment_rating,
    normalize_assessment_trend,
    normalize_claim_status,
    normalize_lifecycle_stage,
)


def test_normalizes_legacy_boundary_variants_to_canonical_values() -> None:
    assert normalize_claim_status("Supported") == "supported"
    assert normalize_claim_status("tavily_synthesized") == "tavily_synthesized"
    assert normalize_assessment_axis("execution") == "execution"
    assert normalize_assessment_axis("Idea \u00d7 Market") == "Idea-Market"
    assert normalize_assessment_rating(" bullish ") == "Bullish"
    assert normalize_assessment_trend("declining") == "Declining"
    assert normalize_lifecycle_stage("memo-ready") == "memo_ready"


@pytest.mark.parametrize(
    "normalizer, value",
    [
        (normalize_claim_status, "pending"),
        (normalize_assessment_axis, "team"),
        (normalize_assessment_rating, "unknown"),
        (normalize_assessment_trend, "flat"),
        (normalize_lifecycle_stage, "archived"),
    ],
)
def test_rejects_unknown_domain_values(normalizer, value: str) -> None:
    with pytest.raises(ValueError):
        normalizer(value)
