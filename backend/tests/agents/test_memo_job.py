"""Tests for opportunity-scoped memo input preparation."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.agents.memo_job import _claim_context, _claim_observation_ids


def test_claim_observation_ids_rejects_malformed_references() -> None:
    claim = MagicMock(observation_ids=[str(uuid.uuid4()), "not-a-uuid"])

    assert _claim_observation_ids(claim) is None


def test_claim_context_includes_claim_and_observation_provenance() -> None:
    claim_id = uuid.uuid4()
    observation_id = uuid.uuid4()
    claim = MagicMock(
        id=claim_id,
        predicate="company_name",
        object_value="Example Labs",
        observation_ids=[str(observation_id)],
    )

    context = _claim_context([claim])

    assert "accepted claims" in context
    assert str(claim_id) in context
    assert str(observation_id) in context
    assert "Example Labs" in context
