"""Tests for the processing pipeline (reconcile, embeddings, dedup)."""

from __future__ import annotations

import pytest

from app.processing.dedup import _cosine_similarity
from app.processing.reconcile import _observation_strength


def test_cosine_similarity_identical_vectors() -> None:
    """Identical vectors should have similarity ~1.0."""
    v = [1.0, 0.0, 0.5]
    assert _cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors() -> None:
    """Orthogonal vectors should have similarity 0.0."""
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert _cosine_similarity(a, b) == 0.0


def test_cosine_similarity_empty_vectors() -> None:
    """Empty or mismatched-length vectors should return 0.0."""
    assert _cosine_similarity([], [1.0]) == 0.0
    assert _cosine_similarity([1.0], [1.0, 2.0]) == 0.0


def test_cosine_similarity_near_duplicate() -> None:
    """Near-duplicate vectors should have high similarity."""
    a = [1.0, 0.9, 0.1]
    b = [1.0, 0.85, 0.15]
    sim = _cosine_similarity(a, b)
    assert sim > 0.92  # above dedup threshold


def test_cosine_similarity_different_vectors() -> None:
    """Different vectors should have low similarity."""
    a = [1.0, 0.0, 0.0, 0.0]
    b = [0.0, 0.0, 0.0, 1.0]
    assert _cosine_similarity(a, b) == 0.0


def test_observation_strength_higher_confidence_is_stronger() -> None:
    """Higher confidence should produce higher strength."""
    from datetime import UTC, datetime
    from unittest.mock import MagicMock

    obs_strong = MagicMock()
    obs_strong.confidence = 0.9
    obs_strong.observed_at = datetime.now(UTC)

    obs_weak = MagicMock()
    obs_weak.confidence = 0.1
    obs_weak.observed_at = datetime.now(UTC)

    assert _observation_strength(obs_strong) > _observation_strength(obs_weak)


def test_observation_strength_newer_is_stronger() -> None:
    """Newer observations should get a recency boost."""
    from datetime import UTC, datetime, timedelta
    from unittest.mock import MagicMock

    obs_new = MagicMock()
    obs_new.confidence = 0.5
    obs_new.observed_at = datetime.now(UTC)

    obs_old = MagicMock()
    obs_old.confidence = 0.5
    obs_old.observed_at = datetime.now(UTC) - timedelta(days=180)

    assert _observation_strength(obs_new) > _observation_strength(obs_old)