"""Versioned thresholds shared by scoring responses and decision UI."""

from typing import Final

RUBRIC_VERSION: Final = "decision-readiness-v1"

# These are eligibility thresholds, not founder-quality judgments. Missing
# values remain unknown and cannot satisfy a threshold.
RUBRIC_THRESHOLDS: Final[dict[str, float]] = {
    "thesis_alignment": 0.75,
    "evidence_confidence": 0.60,
}


def rubric_config() -> dict[str, object]:
    """Return a JSON-safe copy for API responses and audit metadata."""
    return {"version": RUBRIC_VERSION, "thresholds": dict(RUBRIC_THRESHOLDS)}
