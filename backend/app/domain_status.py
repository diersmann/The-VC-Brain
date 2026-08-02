"""Canonical values for statuses exposed by the investment evidence API."""

from __future__ import annotations

from typing import Final, Literal, cast

ClaimStatus = Literal["supported", "contradicted", "unverified", "tavily_synthesized"]
AssessmentAxis = Literal["Founder", "Market", "Idea-Market", "execution", "technical", "commercial"]
AssessmentRating = Literal["Bullish", "Neutral", "Bearish"]
AssessmentTrend = Literal["Improving", "Stable", "Declining"]
LifecycleStage = Literal[
    "discovered",
    "interesting",
    "investigating",
    "contacted",
    "received",
    "memo_ready",
    "hold",
    "approved",
    "closed",
    "screening",
    "triage",
    "diligence",
]

CLAIM_STATUSES: Final = ("supported", "contradicted", "unverified", "tavily_synthesized")
ASSESSMENT_AXES: Final = (
    "Founder",
    "Market",
    "Idea-Market",
    "execution",
    "technical",
    "commercial",
)
ASSESSMENT_RATINGS: Final = ("Bullish", "Neutral", "Bearish")
ASSESSMENT_TRENDS: Final = ("Improving", "Stable", "Declining")
LIFECYCLE_STAGES: Final = (
    "discovered",
    "interesting",
    "investigating",
    "contacted",
    "received",
    "memo_ready",
    "hold",
    "approved",
    "closed",
    "screening",
    "triage",
    "diligence",
)


def normalize_claim_status(value: str) -> ClaimStatus:
    normalized = value.strip().lower().replace("-", "_")
    if normalized not in CLAIM_STATUSES:
        raise ValueError(f"Unsupported claim status: {value}")
    return cast(ClaimStatus, normalized)


def normalize_assessment_axis(value: str) -> AssessmentAxis:
    normalized = value.strip().lower().replace("\u00d7", "-").replace("_", "-")
    normalized = "-".join(part.strip() for part in normalized.split("-"))
    labels = {
        "founder": "Founder",
        "market": "Market",
        "idea-market": "Idea-Market",
        "execution": "execution",
        "technical": "technical",
        "commercial": "commercial",
    }
    try:
        return cast(AssessmentAxis, labels[normalized])
    except KeyError as exc:
        raise ValueError(f"Unsupported assessment axis: {value}") from exc


def normalize_assessment_rating(value: str) -> AssessmentRating:
    normalized = value.strip().lower().capitalize()
    if normalized not in ASSESSMENT_RATINGS:
        raise ValueError(f"Unsupported assessment rating: {value}")
    return cast(AssessmentRating, normalized)


def normalize_assessment_trend(value: str) -> AssessmentTrend:
    normalized = value.strip().lower().capitalize()
    if normalized not in ASSESSMENT_TRENDS:
        raise ValueError(f"Unsupported assessment trend: {value}")
    return cast(AssessmentTrend, normalized)


def normalize_lifecycle_stage(value: str) -> LifecycleStage:
    normalized = value.strip().lower().replace("-", "_")
    if normalized not in LIFECYCLE_STAGES:
        raise ValueError(f"Unsupported lifecycle stage: {value}")
    return cast(LifecycleStage, normalized)
