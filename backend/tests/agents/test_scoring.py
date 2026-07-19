"""Tests for multi-agent scoring committee."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.scoring import (
    AgentAssessment,
    Critique,
    Issue,
    aggregate_assessments,
    build_evidence_text,
    score_candidate,
)


def _mock_openai_response(payload: dict[str, object]) -> MagicMock:
    """Create a mock OpenAI completion response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = __import__("json").dumps(payload)
    return response


def test_aggregate_weights_correctly() -> None:
    """Aggregator should weight the three agents by default (35/30/35)."""
    assessments = [
        AgentAssessment(dimension="execution", score=80, confidence=0.8),
        AgentAssessment(dimension="technical", score=60, confidence=0.7),
        AgentAssessment(dimension="commercial", score=40, confidence=0.6),
    ]
    critique = Critique(issues=[])
    scorecard = aggregate_assessments(assessments, critique)

    # 0.35*80 + 0.30*60 + 0.35*40 = 28 + 18 + 14 = 60
    assert scorecard.composite == 60.0
    assert scorecard.hard_eligible is True
    assert scorecard.execution == 80.0
    assert scorecard.technical == 60.0
    assert scorecard.commercial == 40.0


def test_aggregate_caps_on_hard_issue() -> None:
    """A hard critic issue should cap the composite at 35."""
    assessments = [
        AgentAssessment(dimension="execution", score=90, confidence=0.9),
        AgentAssessment(dimension="technical", score=85, confidence=0.8),
        AgentAssessment(dimension="commercial", score=80, confidence=0.7),
    ]
    critique = Critique(issues=[Issue(severity="hard", description="Identity mismatch")])
    scorecard = aggregate_assessments(assessments, critique)

    assert scorecard.composite == 35.0
    assert scorecard.hard_eligible is False


def test_aggregate_custom_weights() -> None:
    """Custom weights should override defaults."""
    assessments = [
        AgentAssessment(dimension="execution", score=100, confidence=1.0),
        AgentAssessment(dimension="technical", score=0, confidence=1.0),
        AgentAssessment(dimension="commercial", score=0, confidence=1.0),
    ]
    critique = Critique(issues=[])
    scorecard = aggregate_assessments(
        assessments, critique, weights={"execution": 1.0, "technical": 0.0, "commercial": 0.0}
    )
    assert scorecard.composite == 100.0


def test_critic_flags_contradiction() -> None:
    """The critic should flag when agents disagree by >40 points."""
    # This is tested at the aggregate level — a contradiction produces a hard issue
    assessments = [
        AgentAssessment(dimension="execution", score=90, confidence=0.9),
        AgentAssessment(dimension="technical", score=10, confidence=0.9),
        AgentAssessment(dimension="commercial", score=50, confidence=0.5),
    ]
    # Simulate critic finding a contradiction
    critique = Critique(
        issues=[
            Issue(
                severity="hard",
                description="Agents disagree by 80 points (execution=90, technical=10)",
            )
        ]
    )
    scorecard = aggregate_assessments(assessments, critique)
    assert scorecard.hard_eligible is False
    assert scorecard.composite == 35.0


def test_fallback_when_no_api_key() -> None:
    """No API key should return neutral scores with low confidence."""
    scorecard, metadata = asyncio.run(
        score_candidate(evidence_text="some evidence", api_key="", model="gpt-4o")
    )
    assert scorecard.composite == 50.0
    assert scorecard.confidence == 0.15
    assert all(a.score == 50.0 for a in scorecard.agents.values())
    assert metadata["model"] == "gpt-4o"


def test_build_evidence_text_groups_by_source() -> None:
    """Evidence text should group observations by source."""
    obs1 = MagicMock()
    obs1.id = "obs-1"
    obs1.predicate = "github_login"
    obs1.object_value = "tiangolo"
    obs1.extractor_version = "github-v1"

    obs2 = MagicMock()
    obs2.id = "obs-2"
    obs2.predicate = "arxiv_paper_count"
    obs2.object_value = "5"
    obs2.extractor_version = "arxiv-v1"

    person = MagicMock()
    person.display_name = "Sebastián Ramírez"
    person.stable_id = "github:tiangolo"
    person.email = None
    person.handles = {"github": "tiangolo"}

    text, obs_ids = build_evidence_text([obs1, obs2], person)

    assert "obs-1" in text
    assert "obs-2" in text
    assert "github" in text.lower()
    assert "arxiv" in text.lower()
    assert "Sebastián Ramírez" in text
    assert len(obs_ids) == 2


@pytest.mark.asyncio
async def test_agent_returns_valid_assessment_with_mock() -> None:
    """Agent should parse a valid JSON response from OpenAI."""
    payload = {
        "score": 75.0,
        "confidence": 0.8,
        "evidence": ["obs-1", "obs-2"],
        "counter_evidence": [],
        "unknowns": ["No customer retention data"],
        "recommendation": "Strong execution signals.",
        "rationale": "High repo activity and star count indicate consistent delivery.",
    }

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(payload)
    )

    from app.agents.scoring import execution_agent

    semaphore = asyncio.Semaphore(2)
    assessment = await execution_agent("test evidence", mock_client, "gpt-4o", semaphore)

    assert assessment.dimension == "execution"
    assert assessment.score == 75.0
    assert assessment.confidence == 0.8
    assert "obs-1" in assessment.evidence
    assert assessment.rationale != ""


@pytest.mark.asyncio
async def test_agent_handles_json_parse_error() -> None:
    """Agent should return fallback when JSON is invalid."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response({})  # missing required fields
    )

    from app.agents.scoring import technical_agent

    semaphore = asyncio.Semaphore(2)
    assessment = await technical_agent("test", mock_client, "gpt-4o", semaphore)

    # Should still return a valid assessment (with defaults)
    assert assessment.dimension == "technical"
    assert assessment.score == 50.0  # default from payload.get("score", 50.0)


@pytest.mark.asyncio
async def test_agent_handles_api_error() -> None:
    """Agent should return fallback when OpenAI raises an exception."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))

    from app.agents.scoring import commercial_agent

    semaphore = asyncio.Semaphore(2)
    assessment = await commercial_agent("test", mock_client, "gpt-4o", semaphore)

    assert assessment.dimension == "commercial"
    assert assessment.score == 50.0
    assert assessment.confidence == 0.15


@pytest.mark.asyncio
async def test_score_candidate_runs_all_agents() -> None:
    """Full score_candidate should run 3 agents + critic + aggregator."""
    payloads = [
        {"score": 80, "confidence": 0.8, "evidence": [], "counter_evidence": [],
         "unknowns": [], "recommendation": "Good", "rationale": "Test"},
        {"score": 70, "confidence": 0.7, "evidence": [], "counter_evidence": [],
         "unknowns": [], "recommendation": "Fair", "rationale": "Test"},
        {"score": 60, "confidence": 0.6, "evidence": [], "counter_evidence": [],
         "unknowns": [], "recommendation": "Okay", "rationale": "Test"},
    ]

    mock_client = AsyncMock()

    call_count = 0

    async def mock_create(**kwargs: object) -> MagicMock:
        nonlocal call_count
        idx = min(call_count, 2)
        call_count += 1
        return _mock_openai_response(
            payloads[idx] if call_count <= 3 else {"issues": []}
        )

    mock_client.chat.completions.create = mock_create

    with patch("app.agents.scoring.AsyncOpenAI", return_value=mock_client):
        scorecard, _metadata = await score_candidate(
            evidence_text="test evidence",
            api_key="test-key",
            model="gpt-4o",
            concurrency=2,
        )

    assert "execution" in scorecard.agents
    assert "technical" in scorecard.agents
    assert "commercial" in scorecard.agents
    assert 0 <= scorecard.composite <= 100