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
        version="thesis-v001",
        name="Berlin Deep Tech",
        is_active=True,
        stages=["pre-seed", "seed"],
        sectors=["ai", "deep-tech", "b2b"],
        excluded_sectors=[],
        regions=["dach", "europe"],
        check_size_min_k_eur=250,
        check_size_max_k_eur=500,
        ownership_target_pct=10,
        risk_appetite="balanced",
        scoring_weights=DEFAULT_WEIGHTS,
    )


def _observation(predicate: str, value: str, confidence: float = 1.0) -> Observation:
    return Observation(
        id=uuid.uuid4(),
        snapshot_id=uuid.uuid4(),
        subject_id=uuid.uuid4(),
        predicate=predicate,
        object_value=value,
        observed_at=NOW,
        extractor_version="test-v1",
        confidence=confidence,
    )


def test_scores_supported_early_stage_match_without_penalizing_unknown_check() -> None:
    result = score_thesis_alignment(
        _thesis(),
        [
            _observation("pitch_deck_stage", "First round · 2011"),
            _observation("sector", "AI customer service and B2B software"),
            _observation("location", "Dublin, Ireland"),
        ],
    )

    assert result.score == pytest.approx(0.95)
    assert result.hard_eligible is True
    assert result.matched == ["Stage", "Sector", "Geography"]
    assert result.unknown == ["Check size"]
    assert result.criteria["check_size"]["status"] == "unknown"


def test_hard_stage_mismatch_caps_alignment_score() -> None:
    result = score_thesis_alignment(
        _thesis(),
        [
            _observation("pitch_deck_stage", "Series C · 2020"),
            _observation("sector", "B2B SaaS customer operations"),
            _observation("location", "Dublin, Ireland"),
        ],
    )

    assert result.score == pytest.approx(0.35)
    assert result.hard_eligible is False
    assert result.failed == ["Stage"]


def test_missing_evidence_is_neutral_with_low_confidence() -> None:
    result = score_thesis_alignment(_thesis(), [])

    assert result.score == pytest.approx(0.5)
    assert result.confidence == pytest.approx(0.15)
    assert result.hard_eligible is True
    assert result.failed == []
    assert result.unknown == ["Stage", "Sector", "Geography", "Check size"]
