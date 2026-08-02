"""Tests for investment memo generation."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.memo import (
    REQUIRED_SECTIONS,
    MemoSection,
    _validate_memo_citations,
    generate_memo,
)


def _mock_response(payload: dict[str, Any]) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = json.dumps(payload)
    return response


@pytest.mark.asyncio
async def test_memo_has_all_required_sections() -> None:
    """Memo should contain all 5 required sections."""
    payload = {
        "sections": [
            {
                "title": "Company snapshot",
                "text": "Test company.",
                "claim_ids": ["claim-1"],
                "evidence_ids": ["obs-1"],
            },
            {
                "title": "Investment hypotheses",
                "text": "Hypothesis.",
                "claim_ids": ["claim-2"],
                "evidence_ids": ["obs-2"],
            },
            {
                "title": "SWOT",
                "text": "Strengths and weaknesses.",
                "claim_ids": ["claim-3"],
                "evidence_ids": ["obs-3"],
            },
            {
                "title": "Problem and product",
                "text": "Problem and solution.",
                "claim_ids": ["claim-4"],
                "evidence_ids": ["obs-4"],
            },
            {
                "title": "Traction and KPIs",
                "text": "Traction data.",
                "claim_ids": ["claim-5"],
                "evidence_ids": ["obs-5"],
            },
        ]
    }

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=_mock_response(payload))

    semaphore = asyncio.Semaphore(2)
    with patch("app.agents.memo.AsyncOpenAI", return_value=mock_client):
        memo = await generate_memo(
            evidence_text="test",
            scorecard_summary="scores",
            thesis_summary="thesis",
            person_name="Test Person",
            api_key="test-key",
            model="gpt-4o",
            semaphore=semaphore,
        )

    assert len(memo.sections) >= 5
    titles = {s.title for s in memo.sections}
    for required in REQUIRED_SECTIONS:
        assert required in titles
    assert memo.generation_mode == "agent"
    assert memo.status == "succeeded"


@pytest.mark.asyncio
async def test_memo_adds_missing_sections() -> None:
    """Missing required sections should be filled in with placeholders."""
    payload = {
        "sections": [
            {
                "title": "Company snapshot",
                "text": "Test.",
                "claim_ids": ["claim-1"],
                "evidence_ids": ["obs-1"],
            },
        ]
    }

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=_mock_response(payload))

    semaphore = asyncio.Semaphore(2)
    with patch("app.agents.memo.AsyncOpenAI", return_value=mock_client):
        memo = await generate_memo(
            evidence_text="test",
            scorecard_summary="",
            thesis_summary="",
            person_name="Test",
            api_key="test-key",
            model="gpt-4o",
            semaphore=semaphore,
        )

    assert len(memo.sections) == 5
    snapshot = next(s for s in memo.sections if s.title == "Company snapshot")
    assert snapshot.text == "Test."
    swot = next(s for s in memo.sections if s.title == "SWOT")
    assert "not available" in swot.text.lower()
    assert memo.status == "failed"


@pytest.mark.asyncio
async def test_memo_fallback_no_api_key() -> None:
    """No API key should return template fallback with all sections."""
    semaphore = asyncio.Semaphore(2)
    memo = await generate_memo(
        evidence_text="test",
        scorecard_summary="",
        thesis_summary="",
        person_name="Test Person",
        api_key="",
        model="gpt-4o",
        semaphore=semaphore,
    )

    assert memo.generation_mode == "template_fallback"
    assert memo.status == "degraded"
    assert len(memo.sections) == 5
    for section in memo.sections:
        assert "pending" in section.text.lower() or "not available" in section.text.lower()


@pytest.mark.asyncio
async def test_memo_handles_api_error() -> None:
    """API error should fall back to template."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))

    semaphore = asyncio.Semaphore(2)
    with patch("app.agents.memo.AsyncOpenAI", return_value=mock_client):
        memo = await generate_memo(
            evidence_text="test",
            scorecard_summary="",
            thesis_summary="",
            person_name="Test",
            api_key="test-key",
            model="gpt-4o",
            semaphore=semaphore,
        )

    assert memo.generation_mode == "template_fallback"
    assert memo.status == "degraded"
    assert len(memo.sections) == 5


@pytest.mark.asyncio
async def test_memo_evidence_ids_preserved() -> None:
    """Evidence IDs from the LLM response should be preserved."""
    payload = {
        "sections": [
            {
                "title": "Company snapshot",
                "text": "Test.",
                "claim_ids": ["claim-1"],
                "evidence_ids": ["obs-1", "obs-2"],
            },
            {
                "title": "Investment hypotheses",
                "text": "Test.",
                "claim_ids": ["claim-2"],
                "evidence_ids": ["obs-3"],
            },
            {"title": "SWOT", "text": "Not available.", "claim_ids": [], "evidence_ids": []},
            {
                "title": "Problem and product",
                "text": "Not available.",
                "claim_ids": [],
                "evidence_ids": [],
            },
            {
                "title": "Traction and KPIs",
                "text": "Not available.",
                "claim_ids": [],
                "evidence_ids": [],
            },
        ]
    }

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=_mock_response(payload))

    semaphore = asyncio.Semaphore(2)
    with patch("app.agents.memo.AsyncOpenAI", return_value=mock_client):
        memo = await generate_memo(
            evidence_text="test",
            scorecard_summary="",
            thesis_summary="",
            person_name="Test",
            api_key="test-key",
            model="gpt-4o",
            semaphore=semaphore,
        )

    snapshot = next(s for s in memo.sections if s.title == "Company snapshot")
    assert "obs-1" in snapshot.evidence_ids
    assert "obs-2" in snapshot.evidence_ids


def test_memo_citations_are_scoped_and_deterministic() -> None:
    """Unknown IDs fail and valid citations are stored in stable order."""
    sections = [
        MemoSection(
            title="Company snapshot",
            text="Supported fact.",
            claim_ids=["claim-2", "claim-1", "claim-1"],
            evidence_ids=["obs-2", "obs-unknown", "obs-1"],
        )
    ]

    errors = _validate_memo_citations(
        sections,
        allowed_claim_ids=["claim-1", "claim-2"],
        allowed_evidence_ids=["obs-1", "obs-2"],
    )

    assert errors == ["Company snapshot: unknown evidence IDs: obs-unknown"]
    assert sections[0].claim_ids == ["claim-1", "claim-2"]
    assert sections[0].evidence_ids == ["obs-1", "obs-2", "obs-unknown"]
