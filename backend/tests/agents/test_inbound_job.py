"""Tests for safe inbound pitch orchestration boundaries."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents import inbound_job


@pytest.mark.asyncio
async def test_inbound_processing_does_not_bypass_triage_with_memo() -> None:
    snapshot_id = uuid.uuid4()
    person_id = uuid.uuid4()
    opportunity_id = uuid.uuid4()
    snapshot = SimpleNamespace(id=snapshot_id, storage_path="snapshots/deck.pdf")
    session = AsyncMock()
    session.get = AsyncMock(return_value=snapshot)
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    settings = SimpleNamespace(upload_max_pages=10, upload_max_text_chars=1000)
    processing = {"claims_created": 2, "embeddings_generated": 1, "claims_deduped": 0}

    with (
        patch("app.agents.inbound_job._session_ctx") as context,
        patch("app.agents.inbound_job.get_snapshot", new=AsyncMock(return_value=b"pdf")),
        patch(
            "app.agents.inbound_job.extract_pdf_pages",
            return_value=[("deck text", {"kind": "pdf", "page": 1})],
        ),
        patch("app.agents.inbound_job.get_settings", return_value=settings),
        patch(
            "app.agents.inbound_job.process_candidate_job",
            new=AsyncMock(return_value=processing),
        ) as process,
    ):
        context.return_value.__aenter__.return_value = session
        result = await inbound_job.process_inbound_pitch_job(
            {"redis": AsyncMock(), "settings": settings},
            str(person_id),
            str(snapshot_id),
            str(opportunity_id),
            "Example AI",
        )

    process.assert_awaited_once()
    assert result["next_stage"] == "inbound_triage"
    assert result["opportunity_id"] == str(opportunity_id)
    assert result["processing"] == processing
