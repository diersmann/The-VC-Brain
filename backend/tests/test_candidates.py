"""Tests for the candidates API route.

Uses dependency overrides to stub the DB session (no real database).
The pure mapper function is tested directly with hand-built model instances.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.candidates import (
    CandidateResponse,
    map_person_to_candidate,
)
from app.db.models import Person, ScoreSnapshot
from app.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime.now(UTC)


def _make_person(
    *,
    stable_id: str = "person-1",
    display_name: str | None = "Alice Example",
    email: str | None = "alice@example.com",
    consent_state: str = "granted",
) -> Person:
    return Person(
        id=uuid.uuid4(),
        stable_id=stable_id,
        display_name=display_name,
        email=email,
        handles={"linkedin": "alice-example"},
        consent_state=consent_state,
        created_at=NOW,
        updated_at=NOW,
    )


def _make_score_snapshot(
    subject_id: uuid.UUID,
    components: dict[str, object] | None = None,
    rubric_version: str = "founder-v1",
) -> ScoreSnapshot:
    return ScoreSnapshot(
        id=uuid.uuid4(),
        subject_id=subject_id,
        rubric_version=rubric_version,
        components=components or {},
        confidence_interval=None,
        evidence_ids=[],
        created_at=NOW,
        updated_at=NOW,
    )


# ---------------------------------------------------------------------------
# Pure mapper tests (no DB)
# ---------------------------------------------------------------------------


class TestMapPersonToCandidate:
    def test_person_without_scores(self) -> None:
        person = _make_person()
        result = map_person_to_candidate(person)

        assert isinstance(result, CandidateResponse)
        assert result.id == person.id
        assert result.display_name == "Alice Example"
        assert result.scores is None
        assert result.latest_score_at is None
        assert result.origin is None

    def test_person_with_scores(self) -> None:
        person = _make_person()
        score = _make_score_snapshot(
            subject_id=person.id,
            components={
                "novelty": 0.85,
                "momentum": 0.72,
                "thesis_fit": 0.91,
                "evidence_confidence": 0.64,
            },
        )
        result = map_person_to_candidate(person, latest_score=score)

        assert result.scores is not None
        assert result.scores.novelty == 0.85
        assert result.scores.momentum == 0.72
        assert result.scores.thesis_fit == 0.91
        assert result.scores.evidence_confidence == 0.64
        assert result.latest_score_at == NOW

    def test_person_with_partial_scores(self) -> None:
        person = _make_person()
        score = _make_score_snapshot(
            subject_id=person.id,
            components={"novelty": 0.75},  # only one key
        )
        result = map_person_to_candidate(person, latest_score=score)

        assert result.scores is not None
        assert result.scores.novelty == 0.75
        assert result.scores.momentum is None
        assert result.scores.thesis_fit is None
        assert result.scores.evidence_confidence is None

    def test_merges_multi_axis_and_discovery_snapshots(self) -> None:
        person = _make_person()
        multi_axis = _make_score_snapshot(
            subject_id=person.id,
            rubric_version="founder-tavily-v1",
            components={
                "founder": 0.81,
                "market": 0.74,
                "idea_market": 0.69,
                "evidence_confidence": 0.72,
            },
        )
        discovery = _make_score_snapshot(
            subject_id=person.id,
            rubric_version="signal-v1",
            components={"composite": 0.42, "github_signal": 0.8},
        )

        result = map_person_to_candidate(
            person,
            score_snapshots=[discovery, multi_axis],
        )

        assert result.scores is not None
        assert result.scores.founder == 0.81
        assert result.scores.market == 0.74
        assert result.scores.idea_market == 0.69
        assert result.scores.discovery_signal == 0.42
        assert result.scores.raw == {
            "composite": 0.42,
            "github_signal": 0.8,
            "founder": 0.81,
            "market": 0.74,
            "idea_market": 0.69,
            "evidence_confidence": 0.72,
        }

    def test_person_with_origin(self) -> None:
        person = _make_person()
        result = map_person_to_candidate(person, origin="inbound")

        assert result.origin == "inbound"

    def test_person_with_cached_avatar(self) -> None:
        person = _make_person()
        person.avatar_data = b"jpeg-bytes"
        person.avatar_source_type = "linkedin"

        result = map_person_to_candidate(person)

        assert result.avatar_url == f"/api/v1/candidates/{person.id}/avatar"
        assert result.avatar_source == "linkedin"

    def test_person_with_null_display_name(self) -> None:
        person = _make_person(display_name=None)
        result = map_person_to_candidate(person)

        assert result.display_name is None


# ---------------------------------------------------------------------------
# Route tests (stubbed session)
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_session() -> AsyncMock:
    """Return a mock AsyncSession that yields empty query results."""
    session = AsyncMock(spec=AsyncSession)

    # Make session.execute() return an empty result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    return session


def test_list_candidates_returns_empty_list(client: TestClient, mock_session: AsyncMock) -> None:
    """When the DB has no persons, the endpoint returns [].

    Uses dependency override to avoid a real database.
    """
    from app.db import get_session

    async def override_get_session() -> AsyncSession:
        return mock_session

    app.dependency_overrides[get_session] = override_get_session

    try:
        response = client.get("/api/v1/candidates")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_list_candidates_respects_limit_param(client: TestClient, mock_session: AsyncMock) -> None:
    """The limit query parameter is passed through (tested via route registration)."""
    from app.db import get_session

    async def override_get_session() -> AsyncSession:
        return mock_session

    app.dependency_overrides[get_session] = override_get_session

    try:
        response = client.get("/api/v1/candidates?limit=10")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_list_candidates_rejects_invalid_origin(client: TestClient) -> None:
    """Invalid origin values should return 422."""
    response = client.get("/api/v1/candidates?origin=invalid")
    assert response.status_code == 422


def test_list_candidates_rejects_excessive_limit(client: TestClient) -> None:
    """Limit > 200 should return 422."""
    response = client.get("/api/v1/candidates?limit=500")
    assert response.status_code == 422
