from __future__ import annotations

import pytest

from app.agents.outreach import draft_outreach_email
from app.api.routes.candidates import decision_state_for_action


@pytest.mark.asyncio
async def test_outreach_agent_returns_editable_template_without_api_key() -> None:
    draft = await draft_outreach_email(
        founder_name="Alice Chen",
        company="Aperture AI",
        email_type="request_deck",
        brief="Ask about enterprise traction",
        evidence_summary="Public evidence summary",
        api_key="",
        model="gpt-4o",
    )

    assert draft.generation_mode == "template"
    assert "Aperture AI" in draft.subject
    assert "enterprise traction" in draft.body
    assert draft.body.endswith("FirstCheck24 investment team")


@pytest.mark.parametrize(
    ("action", "state"),
    [("proceed", "approved"), ("hold", "hold"), ("decline", "closed")],
)
def test_decision_actions_map_to_auditable_states(action: str, state: str) -> None:
    assert decision_state_for_action(action) == state  # type: ignore[arg-type]
