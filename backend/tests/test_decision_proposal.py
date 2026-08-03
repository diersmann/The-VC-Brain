"""Tests for the deterministic decision proposal contract."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.api.routes.candidates import CandidateDecisionProposalResponse
from app.db.models import DecisionProposal
from app.decision_proposal import DECISION_PROPOSAL_VERSION, build_decision_proposal


def _assessment(axis: str, rating: str, confidence: float, unknowns: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(), axis=axis, rating=rating, confidence=confidence, unknowns=unknowns
    )


def test_proposal_maps_exact_axes_and_persists_readiness_evidence() -> None:
    assessments = [
        _assessment("Founder", "Bullish", 0.82, []),
        _assessment("Market", "Neutral", 0.61, ["Market size needs primary validation"]),
        _assessment("Idea-Market", "Bullish", 0.78, []),
    ]

    proposal = build_decision_proposal(
        assessments=assessments,
        claim_ids=["claim-1", "claim-1", "claim-2"],
        thesis_version="thesis-v3",
        memo_status="succeeded",
        memo_model_version="gpt-test",
        rubric_versions=("founder-agent-v1", "opportunity-axes-v1"),
    )

    assert proposal["action"] == "investigate"
    assert proposal["conviction"] == "medium"
    assert proposal["readiness_status"] == "ready"
    assert proposal["readiness_blockers"] == []
    assert proposal["top_evidence"] == ["claim-1", "claim-2"]
    assert proposal["market_assessment_id"] == str(assessments[1].id)
    assert proposal["open_conditions"] == ["Resolve: Market size needs primary validation"]
    assert proposal["rubric_versions"] == [
        "founder-agent-v1",
        "opportunity-axes-v1",
        DECISION_PROPOSAL_VERSION,
    ]


def test_proposal_exposes_missing_artifacts_without_inventing_values() -> None:
    proposal = build_decision_proposal(
        assessments=[_assessment("Founder", "Bullish", 0.8, [])],
        claim_ids=[],
        thesis_version=None,
        memo_status="pending",
        memo_model_version="gpt-test",
    )

    assert proposal["action"] == "investigate"
    assert proposal["check_amount"] is None
    assert proposal["founder_assessment_id"] is not None
    assert proposal["market_assessment_id"] is None
    assert proposal["idea_market_assessment_id"] is None
    assert proposal["readiness_status"] == "blocked"
    assert proposal["readiness_blockers"] == [
        "missing_market_assessment",
        "missing_idea_market_assessment",
        "memo_not_validated",
    ]


def test_proposal_response_serializes_orm_values_for_candidate_detail() -> None:
    proposal = DecisionProposal(
        id=uuid.uuid4(),
        opportunity_id=uuid.uuid4(),
        action="invest",
        status="draft",
        check_amount=Decimal("100000.00"),
        ownership_target=None,
        conviction="high",
        top_evidence=["claim-1"],
        top_risks=[],
        open_conditions=[],
        readiness_blockers=[],
        readiness_status="ready",
        thesis_version="thesis-v3",
        rubric_versions=[DECISION_PROPOSAL_VERSION],
        memo_model_version="gpt-test",
        override_reason=None,
        created_at=datetime.now(UTC),
    )

    response = CandidateDecisionProposalResponse.model_validate(proposal)

    assert response.check_amount == 100000.0
    assert response.readiness_status == "ready"
