"""Focused tests for automatic pipeline advancement."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.lifecycle_job import advance_pipeline_job


def _result(*, rows: list[object] | None = None, scalar: object = None) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows or []
    result.scalar_one_or_none.return_value = scalar
    return result


def _session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_pipeline_no_opportunities_is_noop() -> None:
    session = _session()
    session.execute = AsyncMock(return_value=_result(rows=[]))
    ctx = {
        "settings": MagicMock(pipeline_batch_size=5),
        "redis": AsyncMock(),
    }

    with patch("app.agents.lifecycle_job._session_ctx") as context:
        context.return_value.__aenter__.return_value = session
        result = await advance_pipeline_job(ctx)

    assert result["opportunities"] == 0
    assert result["transitions"] == 0


@pytest.mark.asyncio
async def test_interesting_candidate_pauses_when_budget_exhausted() -> None:
    person_id = uuid.uuid4()
    opportunity = MagicMock(
        id=uuid.uuid4(),
        lifecycle_state="interesting",
        updated_at=None,
    )
    person = MagicMock(id=person_id)
    session = _session()
    session.execute = AsyncMock(
        side_effect=[
            _result(rows=[opportunity]),
            _result(scalar=person),
        ]
    )
    ctx = {
        "settings": MagicMock(pipeline_batch_size=5),
        "redis": AsyncMock(),
    }

    with (
        patch("app.agents.lifecycle_job._session_ctx") as context,
        patch("app.agents.lifecycle_job._has_score", new=AsyncMock(return_value=False)),
        patch(
            "app.agents.lifecycle_job.get_agent_budget_remaining",
            new=AsyncMock(return_value=0),
        ),
        patch("app.agents.lifecycle_job.queue_enqueue", new=AsyncMock()) as enqueue,
    ):
        context.return_value.__aenter__.return_value = session
        result = await advance_pipeline_job(ctx)

    assert result["budget_exhausted"] == 1
    assert opportunity.lifecycle_state == "interesting"
    enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_investigated_candidate_above_threshold_queues_contact() -> None:
    person_id = uuid.uuid4()
    opportunity = MagicMock(
        id=uuid.uuid4(),
        lifecycle_state="investigating",
        updated_at=None,
    )
    person = MagicMock(id=person_id)
    score = MagicMock(components={"founder": 0.86})
    session = _session()
    session.execute = AsyncMock(
        side_effect=[
            _result(rows=[opportunity]),
            _result(scalar=person),
            _result(scalar=score),
        ]
    )
    ctx = {
        "settings": MagicMock(
            pipeline_batch_size=5,
            contact_threshold=0.65,
        ),
        "redis": AsyncMock(),
    }

    async def transition(_session: Any, opp: Any, new_state: str, **_: object) -> None:
        opp.lifecycle_state = new_state

    with (
        patch("app.agents.lifecycle_job._session_ctx") as context,
        patch("app.agents.lifecycle_job._has_score", new=AsyncMock(return_value=True)),
        patch(
            "app.agents.lifecycle_job.get_agent_budget_remaining",
            new=AsyncMock(return_value=50),
        ),
        patch("app.agents.lifecycle_job.decrement_agent_budget", new=AsyncMock()),
        patch("app.agents.lifecycle_job.transition_opportunity", new=transition),
        patch("app.agents.lifecycle_job.queue_enqueue", new=AsyncMock()) as enqueue,
    ):
        context.return_value.__aenter__.return_value = session
        result = await advance_pipeline_job(ctx)

    assert result["transitions"] == 0
    assert opportunity.lifecycle_state == "investigating"
    enqueue.assert_awaited_once()
    call = enqueue.await_args
    assert call is not None
    assert call.args[1]["job_type"] == "contact_outbound"
