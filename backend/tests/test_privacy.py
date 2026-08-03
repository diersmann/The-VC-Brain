"""Tests for external AI purpose consent and direct-identifier redaction."""

from types import SimpleNamespace

from app.privacy import external_ai_use_decision, redact_direct_identifiers


def _person(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "consent_state": "granted",
        "privacy_legal_basis": "consent",
        "privacy_notice_version": "notice-v2",
        "privacy_purposes": {"scoring": "granted"},
        "privacy_provider_policy_version": "provider-v1",
        "privacy_retention_days": 30,
        "privacy_residency": "eu",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_pending_consent_blocks_external_ai_even_when_policy_is_complete() -> None:
    decision = external_ai_use_decision(_person(consent_state="pending"), "scoring")

    assert decision.allowed is False
    assert decision.reason == "consent_state:pending"


def test_each_external_ai_purpose_requires_an_explicit_grant() -> None:
    decision = external_ai_use_decision(_person(), "memo")

    assert decision.allowed is False
    assert decision.reason == "purpose_not_granted:memo"


def test_granted_policy_allows_purpose_and_redacts_direct_identifiers() -> None:
    decision = external_ai_use_decision(
        _person(privacy_purposes={"scoring": "granted"}), "scoring"
    )

    assert decision.allowed is True
    assert redact_direct_identifiers("Email alice@example.com, phone +49 30 12345678") == (
        "Email [REDACTED_EMAIL], phone [REDACTED_PHONE]"
    )
