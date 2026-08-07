from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.collectors.base import (
    CONNECTOR_READINESS,
    MAX_DISCOVERY_PAGE_SIZE,
    Collected,
    ConnectorError,
    Seed,
    classify_connector_failure,
    validate_collected,
    validate_discovered,
)
from app.collectors.registry import _BUILTIN


class ProviderAgnosticFixtureConnector:
    """Credential-free fixture used to exercise the shared connector boundary."""

    name = "fixture"
    source_type = "fixture"
    authority = 0.5
    cost = 0.1

    async def discover(self, _query: str, page: int = 1) -> list[Seed]:
        pages = {
            1: [Seed("fixture", "founder-one", "Founder One", {"page": 1})],
            2: [Seed("fixture", "founder-two", "Founder Two", {"page": 2})],
        }
        return pages.get(page, [])

    async def collect(self, seed: Seed, _depth: str = "light") -> Collected:
        if seed.handle == "rate-limited":
            raise ConnectorError("HTTP 429 rate limit")
        return Collected(
            content=b"fixture snapshot",
            content_type="text/plain",
            observations=[
                {
                    "predicate": "display_name",
                    "object_value": seed.display_hint,
                    "observed_at": datetime.now(UTC),
                    "source_locator": {
                        "kind": "source_snapshot",
                        "source_uri": f"https://fixture.example/{seed.handle}",
                    },
                }
            ],
            source_type=seed.source_type,
            uri=f"https://fixture.example/{seed.handle}",
            license_hint={"status": "fixture-only"},
        )


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
            observations=[
                {
                    "predicate": "name",
                    "object_value": "Ada",
                    "observed_at": "2026-08-07T10:00:00+00:00",
                }
            ],
            source_type="github",
            uri="https://example.test/source",
        )
    )


@pytest.mark.asyncio
async def test_provider_agnostic_discovery_fixture_keeps_pages_distinct() -> None:
    connector = ProviderAgnosticFixtureConnector()
    first_page = validate_discovered(await connector.discover("founders", page=1))
    second_page = validate_discovered(await connector.discover("founders", page=2))

    assert [seed.handle for seed in first_page] == ["founder-one"]
    assert [seed.handle for seed in second_page] == ["founder-two"]
    assert {seed.handle for seed in first_page}.isdisjoint(
        seed.handle for seed in second_page
    )
    assert all(seed.source_type == connector.source_type for seed in (*first_page, *second_page))


@pytest.mark.asyncio
async def test_provider_agnostic_fixture_validates_provenance_and_partial_failure() -> None:
    connector = ProviderAgnosticFixtureConnector()
    collected = await connector.collect(Seed("fixture", "founder-one", "Founder One"))
    validate_collected(collected)
    assert collected.uri == collected.observations[0]["source_locator"]["source_uri"]

    with pytest.raises(ConnectorError, match="missing observed_at"):
        validate_collected(
            Collected(
                content=b"fixture",
                content_type="text/plain",
                observations=[{"predicate": "name", "object_value": "Ada"}],
                source_type="fixture",
                uri="https://fixture.example/founder-one",
            )
        )

    with pytest.raises(ConnectorError, match="429") as failure:
        await connector.collect(Seed("fixture", "rate-limited", "Rate Limited"))
    assert classify_connector_failure(failure.value) == ("rate_limited", True)


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
        (
            Collected(
                b"source",
                "text/plain",
                [
                    {
                        "predicate": "name",
                        "object_value": "Ada",
                        "observed_at": "not-a-timestamp",
                    }
                ],
                "web",
                "https://example.test",
            ),
            "invalid observed_at",
        ),
        (
            Collected(
                b"source",
                "text/plain",
                [],
                "web",
                "https://example.test",
                license_hint=[],
            ),
            "license hint must be an object",
        ),
        (
            Collected(
                b"source",
                "text/plain",
                [{"predicate": "name", "object_value": None, "observed_at": datetime.now(UTC)}],
                "web",
                "https://example.test",
            ),
            "object_value must be a string",
        ),
        (
            Collected(
                b"source",
                "text/plain",
                [{"predicate": "name", "object_value": 42, "observed_at": datetime.now(UTC)}],
                "web",
                "https://example.test",
            ),
            "object_value must be a string",
        ),
        (
            Collected(
                b"source",
                "text/plain",
                [{"predicate": "name", "object_value": "  ", "observed_at": datetime.now(UTC)}],
                "web",
                "https://example.test",
            ),
            "empty object_value",
        ),
        (
            Collected(
                b"source",
                "text/plain",
                [{"predicate": None, "object_value": "Ada", "observed_at": datetime.now(UTC)}],
                "web",
                "https://example.test",
            ),
            "missing predicate",
        ),
    ],
)
def test_collected_contract_rejects_incomplete_outputs(collected: Collected, message: str) -> None:
    with pytest.raises(ConnectorError, match=message):
        validate_collected(collected)


@pytest.mark.parametrize(
    "seeds, message",
    [
        (None, "discovery output must be a list"),
        ([{"source_type": "fixture", "handle": "founder"}], "seed 0 must be a Seed"),
        ([Seed("", "founder")], "seed 0 is missing source_type"),
        ([Seed("fixture", "")], "seed 0 is missing handle"),
        ([Seed("fixture", "founder", metadata=[])], "seed 0 metadata must be an object"),
        (
            [Seed("fixture", "founder")] * (MAX_DISCOVERY_PAGE_SIZE + 1),
            f"exceeds {MAX_DISCOVERY_PAGE_SIZE} seeds",
        ),
    ],
)
def test_discovery_contract_rejects_malformed_provider_outputs(
    seeds: object, message: str
) -> None:
    with pytest.raises(ConnectorError, match=message):
        validate_discovered(seeds)
