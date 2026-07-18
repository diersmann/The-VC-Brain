"""Candidates (sourcing) API routes.

Provides a read-only list endpoint that maps Person rows to a candidate
DTO suitable for the Sourcing feed. Score fields are null when no
ScoreSnapshot exists for that person.

TODO: Add cursor-based pagination when the dataset grows beyond ~200 rows.
TODO: Add a `subject_type` column to ScoreSnapshot to make the join
      unambiguous. Currently we filter by rubric_version LIKE 'founder%'
      as a heuristic (subject_id is polymorphic — see models.py:279).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.db.models import Opportunity, OpportunityFounder, Person, ScoreSnapshot

router = APIRouter(prefix="/candidates", tags=["candidates"])


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


class CandidateScores(BaseModel):
    """Score components from the latest ScoreSnapshot, if any.

    Keys depend on the rubric_version. Common keys expected by the
    frontend Sourcing feed: novelty, momentum, thesis_fit,
    evidence_confidence. All are optional — missing keys surface as null
    in the UI.
    """

    novelty: float | None = None
    momentum: float | None = None
    thesis_fit: float | None = None
    evidence_confidence: float | None = None
    raw: dict[str, float] | None = None


class CandidateResponse(BaseModel):
    """Public DTO for a sourcing candidate (a Person with optional scores)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stable_id: str
    display_name: str | None = None
    email: str | None = None
    handles: dict[str, str] | None = None
    consent_state: str
    origin: str | None = None
    scores: CandidateScores | None = None
    latest_score_at: datetime | None = None
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Pure mapper (testable without a DB)
# ---------------------------------------------------------------------------


def map_person_to_candidate(
    person: Person,
    latest_score: ScoreSnapshot | None = None,
    origin: str | None = None,
) -> CandidateResponse:
    """Map a Person ORM row (with optional ScoreSnapshot) to a CandidateResponse.

    This is a pure function — no DB access. Unit-test it directly.
    """
    scores: CandidateScores | None = None
    latest_score_at: datetime | None = None

    if latest_score is not None and latest_score.components:
        components: dict[str, Any] = latest_score.components
        scores = CandidateScores(
            novelty=components.get("novelty"),
            momentum=components.get("momentum"),
            thesis_fit=components.get("thesis_fit"),
            evidence_confidence=components.get("evidence_confidence"),
            raw={k: v for k, v in components.items() if isinstance(v, (int, float))},
        )
        latest_score_at = latest_score.created_at

    return CandidateResponse(
        id=person.id,
        stable_id=person.stable_id,
        display_name=person.display_name,
        email=person.email,
        handles=person.handles,
        consent_state=person.consent_state,
        origin=origin,
        scores=scores,
        latest_score_at=latest_score_at,
        created_at=person.created_at,
    )


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

# Heuristic: founder-score rubrics start with "founder" or "person".
# TODO: Replace with a proper subject_type column on ScoreSnapshot.
_FOUNDER_RUBRIC_PATTERN = "founder%"


async def _fetch_latest_scores(
    session: AsyncSession,
    person_ids: list[uuid.UUID],
) -> dict[uuid.UUID, ScoreSnapshot]:
    """Return the latest ScoreSnapshot per person, keyed by person id.

    Uses a correlated subquery to find the max created_at per subject_id,
    filtered to founder-score rubrics.
    """
    if not person_ids:
        return {}

    # Subquery: latest created_at per subject_id for founder rubrics
    latest_per_subject = (
        select(
            ScoreSnapshot.subject_id,
            text("MAX(created_at) AS max_created_at"),
        )
        .where(
            ScoreSnapshot.subject_id.in_(person_ids),
            ScoreSnapshot.rubric_version.like(_FOUNDER_RUBRIC_PATTERN),
        )
        .group_by(ScoreSnapshot.subject_id)
        .subquery()
    )

    result = await session.execute(
        select(ScoreSnapshot)
        .join(
            latest_per_subject,
            (ScoreSnapshot.subject_id == latest_per_subject.c.subject_id)
            & (ScoreSnapshot.created_at == latest_per_subject.c.max_created_at),
        )
    )
    snapshots = result.scalars().all()

    return {s.subject_id: s for s in snapshots}


async def _fetch_origin(
    session: AsyncSession,
    person_ids: list[uuid.UUID],
) -> dict[uuid.UUID, str]:
    """Return the source_kind of the most recent Opportunity per person."""
    if not person_ids:
        return {}

    # Subquery: latest opportunity per person
    latest_opp = (
        select(
            OpportunityFounder.person_id,
            text("MAX(opportunities.created_at) AS max_created"),
        )
        .select_from(OpportunityFounder)
        .join(Opportunity, Opportunity.id == OpportunityFounder.opportunity_id)
        .where(OpportunityFounder.person_id.in_(person_ids))
        .group_by(OpportunityFounder.person_id)
        .subquery()
    )

    result = await session.execute(
        select(
            OpportunityFounder.person_id,
            Opportunity.source_kind,
        )
        .select_from(OpportunityFounder)
        .join(Opportunity, Opportunity.id == OpportunityFounder.opportunity_id)
        .join(
            latest_opp,
            (OpportunityFounder.person_id == latest_opp.c.person_id)
            & (Opportunity.created_at == latest_opp.c.max_created),
        )
    )
    return {row.person_id: row.source_kind for row in result}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=list[CandidateResponse])
async def list_candidates(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(default=50, ge=1, le=200),
    origin: str | None = Query(
        default=None,
        pattern=r"^(inbound|outbound)$",
        description="Filter by opportunity origin (inbound/outbound)",
    ),
) -> list[CandidateResponse]:
    """List sourcing candidates (persons) with optional origin filter.

    Returns persons ordered by creation date (newest first). Scores are
    populated from the latest ScoreSnapshot with a founder-score rubric,
    if one exists.
    """
    # Base query: all persons, newest first
    query = select(Person).order_by(Person.created_at.desc()).limit(limit)

    if origin:
        # Filter to persons who have at least one Opportunity with the
        # given source_kind. Uses the many-to-many join table.
        query = (
            query.join(Person.opportunities)
            .where(Opportunity.source_kind == origin)
            .distinct()
        )

    result = await session.execute(query)
    persons: list[Person] = list(result.scalars().all())

    if not persons:
        return []

    person_ids = [p.id for p in persons]

    # Batch-fetch latest scores and origins
    scores_task = _fetch_latest_scores(session, person_ids)
    origins_task = _fetch_origin(session, person_ids)
    latest_scores, origins = await asyncio.gather(scores_task, origins_task)

    return [
        map_person_to_candidate(
            person=p,
            latest_score=latest_scores.get(p.id),
            origin=origins.get(p.id),
        )
        for p in persons
    ]
