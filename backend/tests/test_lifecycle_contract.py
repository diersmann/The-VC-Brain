"""Tests for the canonical lifecycle contract exposed to clients."""

from fastapi.testclient import TestClient

from app.lifecycle import LIFECYCLE_CONTRACT_VERSION, lifecycle_contract
from app.main import app


def test_contract_is_versioned_and_has_requirements_for_every_stage() -> None:
    contract = lifecycle_contract()
    stages = contract["stages"]

    assert contract["version"] == LIFECYCLE_CONTRACT_VERSION
    assert isinstance(stages, list)
    assert {item["key"] for item in stages} == {
        "discovered",
        "interesting",
        "investigating",
        "contacted",
        "received",
        "triage",
        "screening",
        "diligence",
        "memo_ready",
        "hold",
        "approved",
        "closed",
    }
    assert all(
        item["timestamp_source"]
        == "Opportunity.created_at for initial entry; DecisionEvent.created_at for transitions"
        for item in stages
    )
    assert all(item["entry_requirements"] is not None for item in stages)
    assert all(item["exit_requirements"] is not None for item in stages)


def test_lifecycle_contract_endpoint_returns_the_same_source() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/lifecycle")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == LIFECYCLE_CONTRACT_VERSION
    assert [stage["key"] for stage in payload["stages"]] == [
        stage["key"] for stage in lifecycle_contract()["stages"]
    ]
