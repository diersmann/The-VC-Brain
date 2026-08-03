"""Tests for deny-by-default source-use policy compilation."""

from types import SimpleNamespace

from app.source_policy import (
    SOURCE_POLICY_VERSION,
    build_source_use_policy,
    source_allows_model_use,
)


def test_connector_license_hint_without_model_grant_is_quarantined() -> None:
    policy = build_source_use_policy(
        "github", {"source": "GitHub API", "terms": "https://docs.github.com"}
    )

    assert policy["version"] == SOURCE_POLICY_VERSION
    assert policy["status"] == "unknown"
    assert policy["model_use"] == "denied"
    assert source_allows_model_use(SimpleNamespace(source_use_policy=policy)) is False


def test_explicit_model_grant_allows_model_use_but_not_unrelated_contact() -> None:
    policy = build_source_use_policy("arxiv", {"model_use": "allowed"})

    assert policy["status"] == "allowed"
    assert policy["model_use"] == "allowed"
    assert policy["contact"] == "denied"


def test_founder_provided_deck_has_explicit_internal_use_policy() -> None:
    policy = build_source_use_policy(
        "inbound_deck", {"source": "founder-provided", "model_use": "allowed"}
    )

    assert policy["status"] == "allowed"
    assert policy["collection"] == "allowed"
    assert policy["model_use"] == "allowed"
