"""Tests for the contact outbound job."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.contact_job import contact_outbound_job

_PERSON_ID = uuid.uuid4()
_OPP_ID = uuid.uuid4()


def _mock_person(**overrides: object) -> MagicMock:
    person = MagicMock(
        spec=["id", "stable_id", "display_name", "handles", "email", "consent_state"]
    )
    person.id = _PERSON_ID
    person.stable_id = "github:test"
    person.display_name = "Test"
    person.handles = {"github": "test"}
    person.email = "test@example.com"
    person.consent_state = "pending"
    for k, v in overrides.items():
        setattr(person, k, v)
    return person


def _mock_opportunity(**overrides: object) -> MagicMock:
    opp = MagicMock(spec=["id", "company_name", "lifecycle_state", "source_kind"])
    opp.id = _OPP_ID
    opp.company_name = "Test Co"
    opp.lifecycle_state = "investigating"
    opp.source_kind = "outbound"
    for k, v in overrides.items():
        setattr(opp, k, v)
    return opp


def _make_session() -> AsyncMock:
    """Create a mock session with async add/flush."""
    session = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_contact_outbound_writes_draft_without_claiming_delivery() -> None:
    """contact_outbound_job should persist a draft without marking it sent."""
    mock_ctx = {
        "settings": MagicMock(llm_api_key="", llm_model="gpt-4o"),
        "redis": AsyncMock(),
        "session_factory": MagicMock(),
    }
    session = _make_session()
    session.get = AsyncMock(return_value=_mock_person())

    opportunity = _mock_opportunity()
    opp_result = MagicMock()
    opp_result.scalar_one_or_none = MagicMock(return_value=opportunity)
    empty_result = MagicMock()
    empty_result.scalar_one_or_none = MagicMock(return_value=None)
    session.execute = AsyncMock(side_effect=[opp_result, empty_result])

    with (
        patch("app.agents.contact_job._session_ctx") as mock_ctx_mgr,
        patch(
            "app.agents.contact_job.put_snapshot",
            new=AsyncMock(return_value=("hash", "outreach/hash")),
        ),
    ):
        mock_ctx_mgr.return_value.__aenter__.return_value = session
        result = await contact_outbound_job(mock_ctx, str(_PERSON_ID))

    assert "error" not in result
    assert result["mode"] in ("template", "template_fallback")
    assert result["status"] == "drafted"
    assert opportunity.lifecycle_state == "investigating"


@pytest.mark.asyncio
async def test_contact_outbound_person_not_found() -> None:
    """Missing person should return an error."""
    mock_ctx = {
        "settings": MagicMock(),
        "redis": AsyncMock(),
        "session_factory": MagicMock(),
    }
    session = _make_session()
    session.get = AsyncMock(return_value=None)

    with patch("app.agents.contact_job._session_ctx") as mock_ctx_mgr:
        mock_ctx_mgr.return_value.__aenter__.return_value = session
        result = await contact_outbound_job(mock_ctx, str(_PERSON_ID))

    assert "error" in result
