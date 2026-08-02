"""Tests for the processing pipeline (reconcile, embeddings, dedup)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.processing.dedup import _cosine_similarity
from app.processing.reconcile import _observation_strength, reconcile_observations


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


@pytest.mark.asyncio
async def test_reconcile_keeps_same_predicate_separate_per_opportunity() -> None:
    """A repeated predicate must not create a cross-opportunity claim."""
    person_id = uuid.uuid4()
    opportunity_a = uuid.uuid4()
    opportunity_b = uuid.uuid4()
    observations = []
    for opportunity_id, value in ((opportunity_a, "Company A"), (opportunity_b, "Company B")):
        observation = MagicMock()
        observation.id = uuid.uuid4()
        observation.opportunity_id = opportunity_id
        observation.predicate = "company_name"
        observation.object_value = value
        observation.confidence = 1.0
        observation.observed_at = MagicMock()
        observations.append(observation)

    session = AsyncMock()
    session.execute.return_value = MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=observations)))
    )
    session.add = MagicMock()

    created = await reconcile_observations(session, person_id)

    assert created == 2
    claims = [call.args[0] for call in session.add.call_args_list]
    assert {claim.opportunity_id for claim in claims} == {opportunity_a, opportunity_b}


@pytest.mark.asyncio
async def test_dedup_does_not_merge_claims_across_opportunities() -> None:
    """Near-identical evidence from separate opportunities remains separate."""
    from app.processing.dedup import deduplicate_claims

    opportunity_a = uuid.uuid4()
    opportunity_b = uuid.uuid4()
    claim_a = MagicMock(
        id=uuid.uuid4(),
        observation_ids=[str(uuid.uuid4())],
        predicate="company_name",
        opportunity_id=opportunity_a,
        supersession_id=None,
    )
    claim_b = MagicMock(
        id=uuid.uuid4(),
        observation_ids=[str(uuid.uuid4())],
        predicate="company_name",
        opportunity_id=opportunity_b,
        supersession_id=None,
    )
    obs_a = MagicMock(embedding=[1.0, 0.9])
    obs_b = MagicMock(embedding=[1.0, 0.9])
    claims_result = MagicMock()
    claims_result.scalars.return_value.all.return_value = [claim_a, claim_b]
    obs_result_a = MagicMock()
    obs_result_a.scalar_one_or_none.return_value = obs_a
    obs_result_b = MagicMock()
    obs_result_b.scalar_one_or_none.return_value = obs_b
    session = AsyncMock()
    session.execute.side_effect = [claims_result, obs_result_a, obs_result_b]

    deduplicated = await deduplicate_claims(session, uuid.uuid4())

    assert deduplicated == 0
    assert claim_a.supersession_id is None
    assert claim_b.supersession_id is None
