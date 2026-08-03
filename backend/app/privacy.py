"""Privacy-purpose and PII-minimization gates for external AI providers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

PRIVACY_CONTRACT_VERSION = "privacy-ai-v1"
_SUPPRESSED_CONSENT_STATES = {"pending", "unknown", "opted_out", "suppressed", "do_not_contact"}
_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)")


@dataclass(frozen=True)
class ExternalAIUseDecision:
    """Explain whether a purpose may send data to an external AI provider."""

    allowed: bool
    purpose: str
    reason: str
    contract_version: str = PRIVACY_CONTRACT_VERSION


def external_ai_use_decision(person: Any, purpose: str) -> ExternalAIUseDecision:
    """Return a deny-by-default decision for one person and processing purpose."""
    consent_state = str(getattr(person, "consent_state", "pending") or "pending")
    if consent_state in _SUPPRESSED_CONSENT_STATES:
        return ExternalAIUseDecision(False, purpose, f"consent_state:{consent_state}")
    if not getattr(person, "privacy_legal_basis", None):
        return ExternalAIUseDecision(False, purpose, "privacy_legal_basis_missing")
    if not getattr(person, "privacy_notice_version", None):
        return ExternalAIUseDecision(False, purpose, "privacy_notice_version_missing")
    purposes = getattr(person, "privacy_purposes", None) or {}
    if not isinstance(purposes, dict) or purposes.get(purpose) != "granted":
        return ExternalAIUseDecision(False, purpose, f"purpose_not_granted:{purpose}")
    if not getattr(person, "privacy_provider_policy_version", None):
        return ExternalAIUseDecision(False, purpose, "provider_policy_version_missing")
    retention_days = getattr(person, "privacy_retention_days", None)
    if not isinstance(retention_days, int) or retention_days <= 0:
        return ExternalAIUseDecision(False, purpose, "retention_policy_missing")
    if not getattr(person, "privacy_residency", None):
        return ExternalAIUseDecision(False, purpose, "residency_policy_missing")
    return ExternalAIUseDecision(True, purpose, "policy_granted")


def redact_direct_identifiers(value: str) -> str:
    """Remove email addresses and phone-like strings before external AI use."""
    redacted = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
    return _PHONE_PATTERN.sub("[REDACTED_PHONE]", redacted)
