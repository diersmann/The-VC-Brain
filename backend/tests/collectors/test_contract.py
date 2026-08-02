from __future__ import annotations

import pytest

from app.collectors.base import (
    CONNECTOR_READINESS,
    Collected,
    ConnectorError,
    validate_collected,
)
from app.collectors.registry import _BUILTIN


def test_registered_connectors_have_explicit_readiness_metadata() -> None:
    registered = {source_type for source_type, _module, _class in _BUILTIN}
    assert registered == set(CONNECTOR_READINESS)
    assert all(
        item.contract_version == "connector-contract-v1" for item in CONNECTOR_READINESS.values()
    )
    assert all(
        item.maturity in {"experimental", "beta", "production"}
        for item in CONNECTOR_READINESS.values()
    )


def test_collected_contract_accepts_provenance_and_observations() -> None:
    validate_collected(
        Collected(
            content=b"source",
            content_type="application/json",
            observations=[{"predicate": "name", "object_value": "Ada"}],
            source_type="github",
            uri="https://example.test/source",
        )
    )


@pytest.mark.parametrize(
    "collected, message",
    [
        (Collected(b"", "text/plain", [], "web", "https://example.test"), "empty content"),
        (Collected(b"source", "", [], "web", "https://example.test"), "empty content type"),
        (
            Collected(
                b"source", "text/plain", [{"object_value": "Ada"}], "web", "https://example.test"
            ),
            "missing predicate",
        ),
        (
            Collected(
                b"source", "text/plain", [{"predicate": "name"}], "web", "https://example.test"
            ),
            "missing object_value",
        ),
    ],
)
def test_collected_contract_rejects_incomplete_outputs(collected: Collected, message: str) -> None:
    with pytest.raises(ConnectorError, match=message):
        validate_collected(collected)
