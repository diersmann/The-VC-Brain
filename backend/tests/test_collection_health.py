"""Collection health exposes static connector readiness without health claims."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.routes import collection
from app.collectors.base import CONNECTOR_READINESS
from app.collectors.registry import _BUILTIN


@pytest.mark.asyncio
async def test_collection_health_exposes_readiness_for_every_registered_connector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registered = {source_type for source_type, _module, _class in _BUILTIN}
    monkeypatch.setattr(collection, "queue_depth", AsyncMock(return_value={"collect": 2}))
    monkeypatch.setattr(
        collection,
        "all_connectors",
        lambda: {name: SimpleNamespace() for name in registered},
    )

    response = await collection.collection_health(object())

    assert set(response.connectors) == registered
    assert set(response.connector_readiness) == registered
    for name in registered:
        metadata = CONNECTOR_READINESS[name]
        exposed = response.connector_readiness[name]
        assert exposed.maturity == metadata.maturity
        assert exposed.contract_version == metadata.contract_version
        assert exposed.limitations == list(metadata.limitations)
        # Runtime collection telemetry is not implemented; never fabricate a
        # provider success timestamp from static registration metadata.
        assert exposed.last_success_at is None


def test_collection_health_readiness_schema_is_typed_and_secret_free() -> None:
    response = collection.HealthResponse(
        queue_depth={"collect": 0},
        connectors={"github": "registered"},
        connector_readiness={
            "github": collection.ConnectorReadinessResponse(
                maturity="beta",
                contract_version="connector-contract-v1",
                limitations=["API credentials and rate limits apply"],
            )
        },
    )

    payload = response.model_dump()
    assert set(payload) == {"queue_depth", "connectors", "connector_readiness"}
    assert set(payload["connector_readiness"]["github"]) == {
        "maturity",
        "contract_version",
        "limitations",
        "last_success_at",
    }
    assert payload["connector_readiness"]["github"]["last_success_at"] is None
    # Readiness metadata contains only public contract/limitation text; it must
    # not echo credential values or connector object internals.
    serialized = json.dumps(payload)
    assert "token" not in serialized.lower()
    assert "secret" not in serialized.lower()
    assert "authorization" not in serialized.lower()
