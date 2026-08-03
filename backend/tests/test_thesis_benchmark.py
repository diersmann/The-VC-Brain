"""Labeled regression cases for thesis-fit precision and missing evidence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.db.models import InvestmentThesis, Observation
from app.scoring.thesis import DEFAULT_WEIGHTS, score_thesis_alignment

NOW = datetime.now(UTC)


def _thesis() -> InvestmentThesis:
    return InvestmentThesis(
        id=uuid.uuid4(),
        version="thesis-benchmark-v001",
        name="Benchmark thesis",
        is_active=True,
        stages=["pre-seed", "seed"],
        sectors=["ai", "deep-tech", "b2b"],
        excluded_sectors=["fintech"],
        regions=["dach", "europe"],
        check_size_min_k_eur=250,
        check_size_max_k_eur=500,
        ownership_target_pct=10,
        risk_appetite="balanced",
        scoring_weights=DEFAULT_WEIGHTS,
        discovery_queries=[],
        source_freshness_days={},
    )


def _observation(predicate: str, value: str) -> Observation:
    return Observation(
        id=uuid.uuid4(),
        snapshot_id=uuid.uuid4(),
        subject_id=uuid.uuid4(),
        predicate=predicate,
        object_value=value,
        observed_at=NOW,
        extractor_version="benchmark-v1",
        confidence=1.0,
    )


@pytest.mark.parametrize(
    ("label", "observations", "expected_statuses", "hard_eligible"),
    [
        (
            "supported_match",
            [
                _observation("pitch_deck_stage", "Seed round"),
                _observation("sector", "AI enterprise software"),
                _observation("location", "Berlin, Germany"),
                _observation("requested_check_k_eur", "300"),
            ],
            {
                "stage": "matched",
                "sector": "matched",
                "geography": "matched",
                "check_size": "matched",
            },
            True,
        ),
        (
            "excluded_sector",
            [
                _observation("pitch_deck_stage", "Seed round"),
                _observation("sector", "Fintech payments"),
                _observation("location", "Berlin, Germany"),
            ],
            {
                "stage": "matched",
                "sector": "failed",
                "geography": "matched",
                "check_size": "unknown",
            },
            False,
        ),
        (
            "missing_evidence",
            [],
            {
                "stage": "unknown",
                "sector": "unknown",
                "geography": "unknown",
                "check_size": "unknown",
            },
            True,
        ),
    ],
)
def test_labeled_thesis_benchmark_cases(
    label: str,
    observations: list[Observation],
    expected_statuses: dict[str, str],
    hard_eligible: bool,
) -> None:
    result = score_thesis_alignment(_thesis(), observations)

    assert label
    assert {key: value["status"] for key, value in result.criteria.items()} == expected_statuses
    assert result.hard_eligible is hard_eligible
    assert all("evidence_ids" in criterion for criterion in result.criteria.values())
