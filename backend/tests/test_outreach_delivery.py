"""Outreach suppression and provider-confirmed state transitions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.db.models import OutreachMessage, Person
from app.outreach_delivery import contact_block_reason, transition_provider_state


def _person(*, consent_state: str = "pending", email: str | None = "founder@example.com") -> Person:
    return Person(
        id=uuid.uuid4(),
        stable_id="email:founder@example.com",
        display_name="Founder",
        email=email,
        handles={"email": email} if email else None,
        consent_state=consent_state,
    )


def _message(status: str) -> OutreachMessage:
    now = datetime.now(UTC)
    return OutreachMessage(
        id=uuid.uuid4(),
        opportunity_id=uuid.uuid4(),
        person_id=uuid.uuid4(),
        status=status,
        subject="Hello",
        body="Body",
        created_at=now,
        updated_at=now,
    )


def test_suppression_checks_cover_missing_email_and_opt_out() -> None:
    assert contact_block_reason(_person(email=None)) == "no_verified_recipient_email"
    assert contact_block_reason(_person(consent_state="opted_out")) == (
        "suppressed_consent_state:opted_out"
    )
    assert contact_block_reason(_person()) is None


def test_provider_confirmation_is_required_for_delivery_states() -> None:
    message = _message("send_requested")
    transition_provider_state(message, "sent", provider_message_id="provider-1")
    assert message.status == "sent"
    assert message.sent_at is not None
    assert message.provider_message_id == "provider-1"

    transition_provider_state(message, "delivered", provider_message_id="provider-1")
    assert message.status == "delivered"

    with pytest.raises(ValueError, match="Invalid outreach transition"):
        transition_provider_state(_message("drafted"), "sent")
