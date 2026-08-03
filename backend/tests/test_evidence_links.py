"""Tests for typed claim-to-observation evidence links."""

import uuid

from app.db.models import ClaimObservationLink


def test_claim_observation_link_uses_both_typed_identifiers() -> None:
    claim_id = uuid.uuid4()
    observation_id = uuid.uuid4()

    link = ClaimObservationLink(claim_id=claim_id, observation_id=observation_id)

    assert link.claim_id == claim_id
    assert link.observation_id == observation_id
