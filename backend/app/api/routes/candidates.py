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
from collections import defaultdict
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.outreach import OutreachEmailType, draft_outreach_email
from app.config import get_settings
from app.db import get_session
from app.db.models import (
    Assessment,
    Claim,
    DecisionEvent,
    Observation,
    Opportunity,
    OpportunityFounder,
    Person,
    Relationship,
    ScoreSnapshot,
    SourceSnapshot,
)

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
    founder: float | None = None
    market: float | None = None
    idea_market: float | None = None
    discovery_signal: float | None = None
    evidence_confidence: float | None = None
    raw: dict[str, float] | None = None


class CandidateProfileSummary(BaseModel):
    """Compact evidence-backed profile used by the Discover feed."""

    company: str | None = None
    role: str | None = None
    location: str | None = None
    summary: str | None = None
    website: str | None = None
    deck_url: str | None = None
    deck_title: str | None = None
    deck_stage: str | None = None
    inbound_label: str | None = None
    source_types: list[str] = Field(default_factory=list)
    observation_count: int = 0
    completeness: float = 0.0


class CandidateThesisMatch(BaseModel):
    """Latest explainable alignment against a versioned investment thesis."""

    version: str
    score: float
    confidence: float
    hard_eligible: bool
    matched: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)
    criteria: dict[str, dict[str, object]] = Field(default_factory=dict)


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
    thesis_match: CandidateThesisMatch | None = None
    profile: CandidateProfileSummary | None = None
    avatar_url: str | None = None
    avatar_source: str | None = None
    latest_score_at: datetime | None = None
    created_at: datetime | None = None


class CandidateObservationResponse(BaseModel):
    predicate: str
    object_value: str
    confidence: float
    observed_at: datetime
    source_type: str
    source_uri: str


class CandidateClaimResponse(BaseModel):
    predicate: str
    object_value: str
    status: str
    confidence: float
    created_at: datetime | None = None


class CandidateAssessmentResponse(BaseModel):
    axis: str
    rating: str
    trend: str
    confidence: float
    unknowns: list[str]
    created_at: datetime | None = None


class CandidateScoreResponse(BaseModel):
    rubric_version: str
    components: dict[str, object]
    created_at: datetime | None = None


class CandidateRelationshipResponse(BaseModel):
    relationship_type: str
    person_id: uuid.UUID
    display_name: str | None = None
    confidence: float
    observed_at: datetime


class CandidateOpportunityResponse(BaseModel):
    id: uuid.UUID
    company_name: str
    source_kind: str
    lifecycle_state: str
    thesis_version: str | None = None
    created_at: datetime | None = None


class CandidateDetailResponse(CandidateResponse):
    opportunity: CandidateOpportunityResponse | None = None
    observations: list[CandidateObservationResponse]
    claims: list[CandidateClaimResponse]
    assessments: list[CandidateAssessmentResponse]
    score_history: list[CandidateScoreResponse]
    relationships: list[CandidateRelationshipResponse]


class OutreachDraftRequest(BaseModel):
    email_type: OutreachEmailType = "founder_intro"
    brief: str = Field(default="", max_length=600)


class OutreachDraftResponse(BaseModel):
    subject: str
    body: str
    recipient_email: str | None = None
    generation_mode: Literal["agent", "template", "template_fallback"]
    model: str | None = None
    warning: str | None = None


DecisionAction = Literal["proceed", "hold", "decline"]


class CandidateDecisionRequest(BaseModel):
    action: DecisionAction
    reason: str = Field(min_length=3, max_length=2000)


class CandidateDecisionResponse(BaseModel):
    event_id: uuid.UUID
    prior_state: str
    new_state: str
    action: DecisionAction
    reason: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Pure mapper (testable without a DB)
# ---------------------------------------------------------------------------


def map_person_to_candidate(
    person: Person,
    latest_score: ScoreSnapshot | None = None,
    origin: str | None = None,
    score_snapshots: list[ScoreSnapshot] | None = None,
    profile: CandidateProfileSummary | None = None,
) -> CandidateResponse:
    """Map a Person ORM row (with optional ScoreSnapshot) to a CandidateResponse.

    This is a pure function — no DB access. Unit-test it directly.
    """
    scores: CandidateScores | None = None
    latest_score_at: datetime | None = None

    snapshots = list(score_snapshots or [])
    if latest_score is not None and latest_score not in snapshots:
        snapshots.append(latest_score)
    snapshots.sort(
        key=lambda item: item.created_at.timestamp() if item.created_at is not None else 0.0,
        reverse=True,
    )

    # A signal recomputation must not hide the independently researched
    # Founder/Market/Idea-Market axes. Merge the newest value for every
    # component across rubric versions instead of selecting one snapshot.
    components: dict[str, Any] = {}
    for snapshot in snapshots:
        for key, value in (snapshot.components or {}).items():
            components.setdefault(key, value)

    if components:
        scores = CandidateScores(
            novelty=components.get("novelty"),
            momentum=components.get("momentum"),
            thesis_fit=components.get("thesis_fit"),
            founder=components.get("founder"),
            market=components.get("market"),
            idea_market=components.get("idea_market"),
            discovery_signal=components.get("composite"),
            evidence_confidence=components.get("evidence_confidence"),
            raw={k: v for k, v in components.items() if isinstance(v, (int, float))},
        )
        latest_score_at = snapshots[0].created_at if snapshots else None

    thesis_match: CandidateThesisMatch | None = None
    thesis_snapshot = next(
        (item for item in snapshots if item.rubric_version.startswith("thesis-match-")), None
    )
    if thesis_snapshot is not None:
        thesis_components = thesis_snapshot.components or {}
        thesis_score = thesis_components.get("thesis_fit")
        thesis_confidence = thesis_components.get("thesis_confidence")
        thesis_version = thesis_components.get("thesis_version")
        if (
            isinstance(thesis_score, (int, float))
            and isinstance(thesis_confidence, (int, float))
            and isinstance(thesis_version, str)
        ):
            criteria = thesis_components.get("criteria")
            matched = thesis_components.get("matched")
            failed = thesis_components.get("failed")
            unknown = thesis_components.get("unknown")
            thesis_match = CandidateThesisMatch(
                version=thesis_version,
                score=float(thesis_score),
                confidence=float(thesis_confidence),
                hard_eligible=bool(thesis_components.get("hard_eligible", True)),
                matched=[str(item) for item in matched] if isinstance(matched, list) else [],
                failed=[str(item) for item in failed] if isinstance(failed, list) else [],
                unknown=[str(item) for item in unknown] if isinstance(unknown, list) else [],
                criteria=criteria if isinstance(criteria, dict) else {},
            )

    if profile is not None:
        complete_fields = [
            person.display_name,
            profile.company,
            profile.location,
            profile.summary,
            scores.founder if scores else None,
            scores.market if scores else None,
            scores.idea_market if scores else None,
            profile.observation_count if profile.observation_count else None,
        ]
        profile = profile.model_copy(
            update={
                "completeness": round(sum(value is not None for value in complete_fields) / 8, 3)
            }
        )

    return CandidateResponse(
        id=person.id,
        stable_id=person.stable_id,
        display_name=person.display_name,
        email=person.email,
        handles=person.handles,
        consent_state=person.consent_state,
        origin=origin,
        scores=scores,
        thesis_match=thesis_match,
        profile=profile,
        avatar_url=f"/api/v1/candidates/{person.id}/avatar" if person.avatar_data else None,
        avatar_source=person.avatar_source_type,
        latest_score_at=latest_score_at,
        created_at=person.created_at,
    )


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

# Heuristic: founder-score rubrics start with "founder" or "person".
# TODO: Replace with a proper subject_type column on ScoreSnapshot.
_CANDIDATE_RUBRIC_PATTERNS = ("founder%", "person%", "signal%", "thesis%", "founder-agent%")


def _candidate_rubric_filter() -> Any:
    return or_(
        *(ScoreSnapshot.rubric_version.like(pattern) for pattern in _CANDIDATE_RUBRIC_PATTERNS)
    )


async def _fetch_score_snapshots(
    session: AsyncSession,
    person_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[ScoreSnapshot]]:
    """Return candidate score snapshots grouped newest-first by person."""
    if not person_ids:
        return {}
    result = await session.execute(
        select(ScoreSnapshot)
        .where(
            ScoreSnapshot.subject_id.in_(person_ids),
            _candidate_rubric_filter(),
        )
        .order_by(ScoreSnapshot.created_at.desc())
    )
    grouped: dict[uuid.UUID, list[ScoreSnapshot]] = defaultdict(list)
    for snapshot in result.scalars().all():
        grouped[snapshot.subject_id].append(snapshot)
    return dict(grouped)


async def _fetch_candidate_profiles(
    session: AsyncSession,
    person_ids: list[uuid.UUID],
) -> dict[uuid.UUID, CandidateProfileSummary]:
    """Build compact profiles from persisted observations and provenance."""
    if not person_ids:
        return {}

    result = await session.execute(
        select(Observation, SourceSnapshot)
        .join(SourceSnapshot, SourceSnapshot.id == Observation.snapshot_id)
        .where(Observation.subject_id.in_(person_ids))
        .order_by(Observation.observed_at.desc())
    )
    rows: dict[uuid.UUID, list[tuple[Observation, SourceSnapshot]]] = defaultdict(list)
    for observation, snapshot in result.all():
        if observation.subject_id is not None:
            rows[observation.subject_id].append((observation, snapshot))

    profiles: dict[uuid.UUID, CandidateProfileSummary] = {}
    for person_id, items in rows.items():
        values: dict[str, str] = {}
        source_types: set[str] = set()
        for observation, snapshot in items:
            source_types.add(snapshot.source_type)
            if observation.object_value.strip():
                values.setdefault(observation.predicate.lower(), observation.object_value.strip())

        profiles[person_id] = CandidateProfileSummary(
            company=values.get("company") or values.get("company_name"),
            role=values.get("role") or values.get("title") or values.get("headline"),
            location=values.get("location"),
            summary=(
                values.get("research_founder_summary")
                or values.get("inbound_summary")
                or values.get("bio")
            ),
            website=values.get("blog_url") or values.get("website"),
            deck_url=values.get("pitch_deck_url"),
            deck_title=values.get("pitch_deck_title"),
            deck_stage=values.get("pitch_deck_stage"),
            inbound_label=values.get("inbound_label"),
            source_types=sorted(source_types),
            observation_count=len(items),
        )

    return profiles


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
            func.max(Opportunity.created_at).label("max_created"),
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
        query = query.join(Person.opportunities).where(Opportunity.source_kind == origin).distinct()

    result = await session.execute(query)
    persons: list[Person] = list(result.scalars().all())

    if not persons:
        return []

    person_ids = [p.id for p in persons]

    # Batch-fetch latest scores and origins
    scores_task = _fetch_score_snapshots(session, person_ids)
    origins_task = _fetch_origin(session, person_ids)
    profiles_task = _fetch_candidate_profiles(session, person_ids)
    score_snapshots, origins, profiles = await asyncio.gather(
        scores_task, origins_task, profiles_task
    )

    return [
        map_person_to_candidate(
            person=p,
            origin=origins.get(p.id) or ("outbound" if p.handles else None),
            score_snapshots=score_snapshots.get(p.id),
            profile=profiles.get(p.id),
        )
        for p in persons
    ]


@router.get("/{candidate_id}", response_model=CandidateDetailResponse)
async def get_candidate(
    candidate_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CandidateDetailResponse:
    """Return a candidate with source evidence, scores and opportunity context."""
    person = await session.get(Person, candidate_id)
    if person is None or not person.canonical:
        raise HTTPException(status_code=404, detail="Candidate not found")

    score_snapshots = await _fetch_score_snapshots(session, [person.id])
    origins = await _fetch_origin(session, [person.id])
    profiles = await _fetch_candidate_profiles(session, [person.id])
    candidate = map_person_to_candidate(
        person,
        origin=origins.get(person.id) or ("outbound" if person.handles else None),
        score_snapshots=score_snapshots.get(person.id),
        profile=profiles.get(person.id),
    )

    opportunity_result = await session.execute(
        select(Opportunity)
        .join(OpportunityFounder, OpportunityFounder.opportunity_id == Opportunity.id)
        .where(OpportunityFounder.person_id == person.id)
        .order_by(Opportunity.created_at.desc())
        .limit(1)
    )
    opportunity = opportunity_result.scalar_one_or_none()

    observation_result = await session.execute(
        select(Observation, SourceSnapshot)
        .join(SourceSnapshot, SourceSnapshot.id == Observation.snapshot_id)
        .where(Observation.subject_id == person.id)
        .order_by(Observation.observed_at.desc())
        .limit(200)
    )
    observations = [
        CandidateObservationResponse(
            predicate=observation.predicate,
            object_value=observation.object_value,
            confidence=observation.confidence,
            observed_at=observation.observed_at,
            source_type=snapshot.source_type,
            source_uri=snapshot.uri,
        )
        for observation, snapshot in observation_result.all()
    ]

    claim_result = await session.execute(
        select(Claim)
        .where(Claim.subject_id == person.id)
        .order_by(Claim.created_at.desc())
        .limit(100)
    )
    claims = [
        CandidateClaimResponse(
            predicate=claim.predicate,
            object_value=claim.object_value,
            status=claim.status,
            confidence=claim.confidence,
            created_at=claim.created_at,
        )
        for claim in claim_result.scalars().all()
    ]

    assessments: list[CandidateAssessmentResponse] = []
    if opportunity is not None:
        assessment_result = await session.execute(
            select(Assessment)
            .where(Assessment.opportunity_id == opportunity.id)
            .order_by(Assessment.created_at.desc())
        )
        assessments = [
            CandidateAssessmentResponse(
                axis=item.axis,
                rating=item.rating,
                trend=item.trend,
                confidence=item.confidence,
                unknowns=item.unknowns,
                created_at=item.created_at,
            )
            for item in assessment_result.scalars().all()
        ]

    history_result = await session.execute(
        select(ScoreSnapshot)
        .where(ScoreSnapshot.subject_id == person.id, _candidate_rubric_filter())
        .order_by(ScoreSnapshot.created_at.asc())
        .limit(100)
    )
    score_history = [
        CandidateScoreResponse(
            rubric_version=item.rubric_version,
            components=item.components,
            created_at=item.created_at,
        )
        for item in history_result.scalars().all()
    ]

    relationship_result = await session.execute(
        select(Relationship).where(
            or_(
                Relationship.person_a_id == person.id,
                Relationship.person_b_id == person.id,
            )
        )
    )
    relationship_rows = list(relationship_result.scalars().all())
    counterpart_ids = {
        item.person_b_id if item.person_a_id == person.id else item.person_a_id
        for item in relationship_rows
    }
    counterpart_names: dict[uuid.UUID, str | None] = {}
    if counterpart_ids:
        counterpart_result = await session.execute(
            select(Person.id, Person.display_name).where(Person.id.in_(counterpart_ids))
        )
        counterpart_names = {
            person_id: display_name for person_id, display_name in counterpart_result.tuples().all()
        }

    relationships = []
    for item in relationship_rows:
        counterpart_id = item.person_b_id if item.person_a_id == person.id else item.person_a_id
        relationships.append(
            CandidateRelationshipResponse(
                relationship_type=item.relationship_type,
                person_id=counterpart_id,
                display_name=counterpart_names.get(counterpart_id),
                confidence=item.confidence,
                observed_at=item.observed_at,
            )
        )

    return CandidateDetailResponse(
        **candidate.model_dump(),
        opportunity=(
            CandidateOpportunityResponse(
                id=opportunity.id,
                company_name=opportunity.company_name,
                source_kind=opportunity.source_kind,
                lifecycle_state=opportunity.lifecycle_state,
                thesis_version=opportunity.thesis_version,
                created_at=opportunity.created_at,
            )
            if opportunity is not None
            else None
        ),
        observations=observations,
        claims=claims,
        assessments=assessments,
        score_history=score_history,
        relationships=relationships,
    )


def decision_state_for_action(action: DecisionAction) -> str:
    """Map an explicit human decision to its auditable lifecycle state."""
    return {"proceed": "approved", "hold": "hold", "decline": "closed"}[action]


@router.post("/{candidate_id}/decision", response_model=CandidateDecisionResponse)
async def record_candidate_decision(
    candidate_id: uuid.UUID,
    payload: CandidateDecisionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CandidateDecisionResponse:
    """Persist a human VC decision and update the latest opportunity state."""
    person = await session.get(Person, candidate_id)
    if person is None or not person.canonical:
        raise HTTPException(status_code=404, detail="Candidate not found")

    opportunity_result = await session.execute(
        select(Opportunity)
        .join(OpportunityFounder, OpportunityFounder.opportunity_id == Opportunity.id)
        .where(OpportunityFounder.person_id == person.id)
        .order_by(Opportunity.created_at.desc())
        .limit(1)
    )
    opportunity = opportunity_result.scalar_one_or_none()
    if opportunity is None:
        raise HTTPException(status_code=409, detail="Candidate has no opportunity to decide")

    prior_state = opportunity.lifecycle_state
    new_state = decision_state_for_action(payload.action)
    reason = payload.reason.strip()
    event = DecisionEvent(
        opportunity_id=opportunity.id,
        prior_state=prior_state,
        new_state=new_state,
        actor="vc-ui:sophie-werner",
        reason=reason,
        sla_metadata={"action": payload.action, "source": "decision-floating-dock"},
    )
    opportunity.lifecycle_state = new_state
    session.add(event)
    await session.commit()
    await session.refresh(event)

    return CandidateDecisionResponse(
        event_id=event.id,
        prior_state=prior_state,
        new_state=new_state,
        action=payload.action,
        reason=reason,
        created_at=event.created_at,
    )


@router.post("/{candidate_id}/outreach-draft", response_model=OutreachDraftResponse)
async def create_outreach_draft(
    candidate_id: uuid.UUID,
    payload: OutreachDraftRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OutreachDraftResponse:
    """Create a human-reviewable outreach email from stored candidate evidence."""
    person = await session.get(Person, candidate_id)
    if person is None or not person.canonical:
        raise HTTPException(status_code=404, detail="Candidate not found")

    profiles = await _fetch_candidate_profiles(session, [person.id])
    score_snapshots = await _fetch_score_snapshots(session, [person.id])
    profile = profiles.get(person.id)
    candidate = map_person_to_candidate(
        person,
        score_snapshots=score_snapshots.get(person.id),
        profile=profile,
    )
    company = profile.company if profile and profile.company else "the company"
    evidence_parts = [
        f"Role: {profile.role}" if profile and profile.role else "",
        f"Location: {profile.location}" if profile and profile.location else "",
        f"Summary: {profile.summary}" if profile and profile.summary else "",
        f"Website: {profile.website}" if profile and profile.website else "",
        (
            "Independent scores: "
            f"Founder={candidate.scores.founder}, Market={candidate.scores.market}, "
            f"Idea-Market={candidate.scores.idea_market}"
            if candidate.scores
            else ""
        ),
    ]
    settings = get_settings()
    draft = await draft_outreach_email(
        founder_name=person.display_name or "Founder",
        company=company,
        email_type=payload.email_type,
        brief=payload.brief.strip(),
        evidence_summary="\n".join(item for item in evidence_parts if item),
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )
    return OutreachDraftResponse(
        **draft.model_dump(),
        recipient_email=person.email,
    )


@router.get(
    "/{candidate_id}/avatar",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}, "image/png": {}, "image/webp": {}}}},
)
async def get_candidate_avatar(
    candidate_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    """Serve the cached avatar bytes stored on a canonical Person."""
    person = await session.get(Person, candidate_id)
    if person is None or not person.canonical or not person.avatar_data:
        raise HTTPException(status_code=404, detail="Candidate avatar not found")

    headers = {"Cache-Control": "public, max-age=86400"}
    if person.avatar_sha256:
        headers["ETag"] = f'"{person.avatar_sha256}"'
    return Response(
        content=person.avatar_data,
        media_type=person.avatar_mime_type or "image/jpeg",
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Investment memo routes
# ---------------------------------------------------------------------------


class MemoResponse(BaseModel):
    """A generated investment memo."""

    sections: list[dict[str, object]]
    generation_mode: str | None = None
    model_version: str | None = None
    created_at: datetime | None = None


@router.get("/{candidate_id}/memo", response_model=MemoResponse)
async def get_candidate_memo(
    candidate_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MemoResponse:
    """Return the latest investment memo for a candidate."""
    from app.db.models import InvestmentMemo

    result = await session.execute(
        select(InvestmentMemo)
        .join(Opportunity, Opportunity.id == InvestmentMemo.opportunity_id)
        .join(OpportunityFounder, OpportunityFounder.opportunity_id == Opportunity.id)
        .where(OpportunityFounder.person_id == candidate_id)
        .order_by(InvestmentMemo.created_at.desc())
        .limit(1)
    )
    memo = result.scalar_one_or_none()
    if memo is None:
        raise HTTPException(status_code=404, detail="No memo found for this candidate")

    sections = memo.sections.get("sections", []) if isinstance(memo.sections, dict) else []
    return MemoResponse(
        sections=sections,
        generation_mode=(
            memo.sections.get("generation_mode")
            if isinstance(memo.sections, dict) else None
        ),
        model_version=memo.model_version,
        created_at=memo.created_at,
    )


@router.post("/{candidate_id}/memo/generate", response_model=dict[str, str])
async def generate_candidate_memo(
    candidate_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """Queue investment memo generation for a candidate."""
    person = await session.get(Person, candidate_id)
    if person is None or not person.canonical:
        raise HTTPException(status_code=404, detail="Candidate not found")

    import redis.asyncio as aioredis

    from app.collectors.queue import enqueue as queue_enqueue
    from app.config import get_settings

    settings = get_settings()
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
    try:
        await queue_enqueue(
            redis,
            {"job_type": "generate_memo", "person_id": str(person.id)},
            priority=10.0,
        )
    finally:
        await redis.aclose()

    return {"message": f"Memo generation queued for {candidate_id}"}
