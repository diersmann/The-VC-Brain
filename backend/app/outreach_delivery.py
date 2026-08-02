"""Outreach suppression checks and provider delivery-state transitions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from app.db.models import OutreachMessage, Person

OutreachStatus = Literal[
    "drafted",
    "approved",
    "send_requested",
    "sent",
    "delivered",
    "bounced",
    "replied",
    "opted_out",
    "failed",
]

_SUPPRESSED_CONSENT_STATES = {"opted_out", "suppressed", "do_not_contact"}
_DELIVERY_TRANSITIONS: dict[str, set[str]] = {
    "send_requested": {"sent", "failed"},
    "sent": {"delivered", "bounced", "replied", "opted_out"},
    "delivered": {"replied", "opted_out"},
    "replied": {"opted_out"},
}


def contact_block_reason(person: Person) -> str | None:
    if not person.email:
        return "no_verified_recipient_email"
    if person.consent_state in _SUPPRESSED_CONSENT_STATES:
        return f"suppressed_consent_state:{person.consent_state}"
    return None


def transition_provider_state(
    message: OutreachMessage,
    new_status: OutreachStatus,
    *,
    provider_message_id: str | None = None,
    failure_reason: str | None = None,
) -> None:
    """Apply only provider-confirmed delivery events to a message."""
    if new_status not in _DELIVERY_TRANSITIONS.get(message.status, set()):
        raise ValueError(f"Invalid outreach transition: {message.status} -> {new_status}")
    now = datetime.now(UTC)
    message.status = new_status
    message.provider_message_id = provider_message_id or message.provider_message_id
    message.failure_reason = failure_reason
    if new_status == "sent":
        message.sent_at = now
