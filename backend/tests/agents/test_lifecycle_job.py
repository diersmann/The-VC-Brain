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
        patch(
            "app.agents.lifecycle_job._has_opportunity_axes", new=AsyncMock(return_value=False)
        ),
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
        patch(
            "app.agents.lifecycle_job._has_opportunity_axes", new=AsyncMock(return_value=True)
        ),
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


@pytest.mark.asyncio
async def test_received_inbound_queues_processing_before_triage() -> None:
    person_id = uuid.uuid4()
    opportunity = MagicMock(
        id=uuid.uuid4(),
        lifecycle_state="received",
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
        "settings": MagicMock(pipeline_batch_size=5, pipeline_stuck_after_minutes=30),
        "redis": AsyncMock(),
    }

    with (
        patch("app.agents.lifecycle_job._session_ctx") as context,
        patch(
            "app.agents.lifecycle_job._has_scoped_claims", new=AsyncMock(return_value=False)
        ),
        patch(
            "app.agents.lifecycle_job._has_recent_pipeline_event",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.agents.lifecycle_job.get_agent_budget_remaining",
            new=AsyncMock(return_value=50),
        ),
        patch("app.agents.lifecycle_job.decrement_agent_budget", new=AsyncMock()),
        patch("app.agents.lifecycle_job.queue_enqueue", new=AsyncMock()) as enqueue,
    ):
        context.return_value.__aenter__.return_value = session
        result = await advance_pipeline_job(ctx)

    assert result["transitions"] == 0
    assert opportunity.lifecycle_state == "received"
    enqueue.assert_awaited_once()
    assert enqueue.await_args.args[1] == {
        "job_type": "process_candidate",
        "person_id": str(person.id),
    }
    event = session.add.call_args.args[0]
    assert event.reason == "Inbound processing queued"
    assert event.sla_metadata["pipeline_stage"] == "received"


@pytest.mark.asyncio
async def test_received_inbound_advances_to_triage_after_processing() -> None:
    opportunity = MagicMock(id=uuid.uuid4(), lifecycle_state="received", updated_at=None)
    person = MagicMock(id=uuid.uuid4())
    session = _session()
    session.execute = AsyncMock(side_effect=[_result(rows=[opportunity]), _result(scalar=person)])
    ctx = {
        "settings": MagicMock(pipeline_batch_size=5, pipeline_stuck_after_minutes=30),
        "redis": AsyncMock(),
    }

    async def transition(_session: Any, opp: Any, new_state: str, **_: object) -> None:
        opp.lifecycle_state = new_state

    with (
        patch("app.agents.lifecycle_job._session_ctx") as context,
        patch("app.agents.lifecycle_job._has_scoped_claims", new=AsyncMock(return_value=True)),
        patch("app.agents.lifecycle_job.transition_opportunity", new=transition),
        patch("app.agents.lifecycle_job.queue_enqueue", new=AsyncMock()) as enqueue,
    ):
        context.return_value.__aenter__.return_value = session
        result = await advance_pipeline_job(ctx)

    assert result["transitions"] == 1
    assert opportunity.lifecycle_state == "triage"
    enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_triage_queues_founder_score_before_screening() -> None:
    opportunity = MagicMock(id=uuid.uuid4(), lifecycle_state="triage", updated_at=None)
    person = MagicMock(id=uuid.uuid4())
    session = _session()
    session.execute = AsyncMock(side_effect=[_result(rows=[opportunity]), _result(scalar=person)])
    ctx = {
        "settings": MagicMock(pipeline_batch_size=5, pipeline_stuck_after_minutes=30),
        "redis": AsyncMock(),
    }

    with (
        patch("app.agents.lifecycle_job._session_ctx") as context,
        patch("app.agents.lifecycle_job._has_founder_score", new=AsyncMock(return_value=False)),
        patch(
            "app.agents.lifecycle_job._has_recent_pipeline_event",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.agents.lifecycle_job.get_agent_budget_remaining",
            new=AsyncMock(return_value=5),
        ),
        patch("app.agents.lifecycle_job.decrement_agent_budget", new=AsyncMock()),
        patch("app.agents.lifecycle_job.queue_enqueue", new=AsyncMock()) as enqueue,
    ):
        context.return_value.__aenter__.return_value = session
        await advance_pipeline_job(ctx)

    enqueue.assert_awaited_once()
    assert enqueue.await_args.args[1] == {
        "job_type": "score_candidate",
        "person_id": str(person.id),
    }
    assert session.add.call_args.args[0].reason == "Founder Score queued"


@pytest.mark.asyncio
async def test_screening_queues_opportunity_research_before_diligence() -> None:
    opportunity = MagicMock(id=uuid.uuid4(), lifecycle_state="screening", updated_at=None)
    person = MagicMock(id=uuid.uuid4())
    session = _session()
    session.execute = AsyncMock(side_effect=[_result(rows=[opportunity]), _result(scalar=person)])
    ctx = {
        "settings": MagicMock(pipeline_batch_size=5, pipeline_stuck_after_minutes=30),
        "redis": AsyncMock(),
    }

    with (
        patch("app.agents.lifecycle_job._session_ctx") as context,
        patch(
            "app.agents.lifecycle_job._has_opportunity_axes", new=AsyncMock(return_value=False)
        ),
        patch(
            "app.agents.lifecycle_job._has_recent_pipeline_event",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.agents.lifecycle_job.get_agent_budget_remaining",
            new=AsyncMock(return_value=3),
        ),
        patch("app.agents.lifecycle_job.decrement_agent_budget", new=AsyncMock()),
        patch("app.agents.lifecycle_job.queue_enqueue", new=AsyncMock()) as enqueue,
    ):
        context.return_value.__aenter__.return_value = session
        await advance_pipeline_job(ctx)

    enqueue.assert_awaited_once()
    assert enqueue.await_args.args[1] == {
        "job_type": "research_candidate",
        "person_id": str(person.id),
        "opportunity_id": str(opportunity.id),
    }
    assert session.add.call_args.args[0].reason == "Opportunity research queued"


@pytest.mark.asyncio
async def test_diligence_queues_memo_before_memo_ready() -> None:
    opportunity = MagicMock(id=uuid.uuid4(), lifecycle_state="diligence", updated_at=None)
    person = MagicMock(id=uuid.uuid4())
    session = _session()
    session.execute = AsyncMock(side_effect=[_result(rows=[opportunity]), _result(scalar=person)])
    ctx = {
        "settings": MagicMock(pipeline_batch_size=5, pipeline_stuck_after_minutes=30),
        "redis": AsyncMock(),
    }

    with (
        patch("app.agents.lifecycle_job._session_ctx") as context,
        patch("app.agents.lifecycle_job._has_memo", new=AsyncMock(return_value=False)),
        patch(
            "app.agents.lifecycle_job._has_recent_pipeline_event",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.agents.lifecycle_job.get_agent_budget_remaining",
            new=AsyncMock(return_value=1),
        ),
        patch("app.agents.lifecycle_job.decrement_agent_budget", new=AsyncMock()),
        patch("app.agents.lifecycle_job.queue_enqueue", new=AsyncMock()) as enqueue,
    ):
        context.return_value.__aenter__.return_value = session
        await advance_pipeline_job(ctx)

    enqueue.assert_awaited_once()
    assert enqueue.await_args.args[1] == {
        "job_type": "generate_memo",
        "person_id": str(person.id),
        "opportunity_id": str(opportunity.id),
    }
    assert session.add.call_args.args[0].reason == "Memo generation queued"
