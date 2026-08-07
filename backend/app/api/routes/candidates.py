"""Candidates (sourcing) API routes.

Provides a read-only list endpoint that maps Person rows to a candidate
DTO suitable for the Sourcing feed. Score fields are null when no
ScoreSnapshot exists for that person.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.outreach import OutreachEmailType, draft_outreach_email
from app.client_lifecycle import redis_connection
from app.config import get_settings
from app.db import get_session
from app.db.models import (
    Assessment,
    CandidateFeedback,
    Claim,
    DecisionEvent,
    DecisionProposal,
    InvestmentMemo,
    Observation,
    Opportunity,
    OpportunityFounder,
    OutreachMessage,
    Person,
    Relationship,
    ScoreSnapshot,
    SourceSnapshot,
)
from app.domain_status import (
    AssessmentAxis,
    AssessmentRating,
    AssessmentTrend,
    ClaimStatus,
    LifecycleStage,
    normalize_assessment_axis,
    normalize_assessment_rating,
    normalize_assessment_trend,
    normalize_claim_status,
    normalize_lifecycle_stage,
)
from app.job_ledger import create_job, update_job
from app.lifecycle import is_valid_transition
from app.privacy import external_ai_use_decision, redact_direct_identifiers
from app.sla import evaluate_sla, finalize_sla

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


class CandidateSLAResponse(BaseModel):
    """Persisted decision clock plus its current derived risk state."""

    received_at: datetime | None = None
    decision_due_at: datetime | None = None
    stage_deadlines: dict[str, datetime] = Field(default_factory=dict)
    owner: str | None = None
    pause_reason: str | None = None
    stage: str | None = None
    status: Literal["not_started", "on_track", "at_risk", "breached", "paused", "met"]
    attainment: Literal["pending", "met", "breached"]
    remaining_seconds: int | None = None
    stage_remaining_seconds: int | None = None
    elapsed_seconds: int | None = None
    alert: bool = False
    alert_level: Literal["none", "warning", "breach", "paused"]


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
    lifecycle_stage: LifecycleStage | None = None
    sla: CandidateSLAResponse | None = None

    @field_validator("lifecycle_stage", mode="before")
    @classmethod
    def canonical_lifecycle_stage(cls, value: str | None) -> LifecycleStage | None:
        return None if value is None else normalize_lifecycle_stage(value)


class CandidateListResponse(BaseModel):
    """Versioned, cursor-paginated candidate collection response.

    The legacy array response remains available unless the caller requests
    ``application/vnd.the-vc-brain.candidates.v1+json``. This lets existing
    consumers migrate without a flag day while new consumers get authoritative
    totals and a deterministic continuation cursor.
    """

    version: Literal["v1"] = "v1"
    items: list[CandidateResponse]
    next_cursor: str | None = None
    total_count: int
    limit: int
    search: str | None = None
    filters: dict[str, str] = Field(default_factory=dict)


class CandidateObservationResponse(BaseModel):
    id: uuid.UUID
    predicate: str
    object_value: str
    confidence: float
    source_locator: dict[str, object] | None = None
    observed_at: datetime
    source_type: str
    source_uri: str


class CandidateClaimResponse(BaseModel):
    id: uuid.UUID
    predicate: str
    object_value: str
    status: ClaimStatus

    @field_validator("status", mode="before")
    @classmethod
    def canonical_claim_status(cls, value: str) -> ClaimStatus:
        return normalize_claim_status(value)
    confidence: float
    trust_score: float | None = None
    trust_interval: dict[str, float] | None = None
    trust_components: dict[str, object] | None = None
    trust_explanation: str | None = None
    created_at: datetime | None = None


class CandidateAssessmentResponse(BaseModel):
    axis: AssessmentAxis
    rating: AssessmentRating
    trend: AssessmentTrend
    confidence: float
    unknowns: list[str]
    created_at: datetime | None = None

    @field_validator("axis", mode="before")
    @classmethod
    def canonical_axis(cls, value: str) -> AssessmentAxis:
        return normalize_assessment_axis(value)

    @field_validator("rating", mode="before")
    @classmethod
    def canonical_rating(cls, value: str) -> AssessmentRating:
        return normalize_assessment_rating(value)

    @field_validator("trend", mode="before")
    @classmethod
    def canonical_trend(cls, value: str) -> AssessmentTrend:
        return normalize_assessment_trend(value)


class CandidateScoreResponse(BaseModel):
    rubric_version: str
    components: dict[str, object]
    created_at: datetime | None = None


class CandidateDecisionProposalResponse(BaseModel):
    """Structured proposal and readiness snapshot for human review."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action: Literal["invest", "hold", "investigate", "decline"]
    status: Literal["draft", "approved", "overridden"]
    check_amount: float | None = None
    ownership_target: float | None = None
    conviction: Literal["low", "medium", "high"] | None = None
    founder_assessment_id: uuid.UUID | None = None
    market_assessment_id: uuid.UUID | None = None
    idea_market_assessment_id: uuid.UUID | None = None
    top_evidence: list[str] = Field(default_factory=list)
    top_risks: list[str] = Field(default_factory=list)
    open_conditions: list[str] = Field(default_factory=list)
    readiness_blockers: list[str] = Field(default_factory=list)
    readiness_status: Literal["ready", "blocked"]
    thesis_version: str | None = None
    rubric_versions: list[str] = Field(default_factory=list)
    memo_model_version: str | None = None
    override_reason: str | None = None
    created_at: datetime | None = None


class CandidateRelationshipResponse(BaseModel):
    relationship_type: str
    person_id: uuid.UUID
    display_name: str | None = None
    confidence: float
    observed_at: datetime


class CandidateOpportunityResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None = None
    company_name: str
    source_kind: str
    lifecycle_state: LifecycleStage

    @field_validator("lifecycle_state", mode="before")
    @classmethod
    def canonical_lifecycle_state(cls, value: str) -> LifecycleStage:
        return normalize_lifecycle_stage(value)
    thesis_version: str | None = None
    created_at: datetime | None = None


class CandidateDetailResponse(CandidateResponse):
    opportunity: CandidateOpportunityResponse | None = None
    decision_proposal: CandidateDecisionProposalResponse | None = None
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


class OutreachApprovalRequest(BaseModel):
    approved_by: str = Field(min_length=1, max_length=128)


class OutreachActionResponse(BaseModel):
    outreach_id: uuid.UUID
    status: str
    recipient_email: str | None = None
    detail: str


DecisionAction = Literal["proceed", "hold", "decline"]


class CandidateDecisionRequest(BaseModel):
    opportunity_id: uuid.UUID
    action: DecisionAction
    reason: str = Field(min_length=3, max_length=2000)


class CandidateDecisionResponse(BaseModel):
    event_id: uuid.UUID
    prior_state: str
    new_state: str
    action: DecisionAction
    reason: str
    created_at: datetime


FeedbackAction = Literal["dismiss", "save", "defer", "assign"]


class CandidateFeedbackRequest(BaseModel):
    action: FeedbackAction
    reason: str = Field(min_length=3, max_length=2000)


class CandidateFeedbackResponse(BaseModel):
    id: uuid.UUID
    person_id: uuid.UUID
    action: FeedbackAction
    reason: str
    actor: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Pure mapper (testable without a DB)
# ---------------------------------------------------------------------------


def map_person_to_candidate(
    person: Person,
    latest_score: ScoreSnapshot | None = None,
    origin: str | None = None,
    score_snapshots: list[ScoreSnapshot] | None = None,
    opportunity_score: ScoreSnapshot | None = None,
    profile: CandidateProfileSummary | None = None,
    lifecycle_stage: str | None = None,
    sla: CandidateSLAResponse | None = None,
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

    # Only person-scoped snapshots contribute to the persistent Founder Score,
    # sourcing signal, and thesis alignment. Opportunity axes are attached
    # separately below so a repeat founder's company cannot inherit another
    # opportunity's Market or Idea-vs-Market value.
    components: dict[str, Any] = {}
    for snapshot in snapshots:
        for key, value in (snapshot.components or {}).items():
            if key in {"market", "idea_market"}:
                continue
            components.setdefault(key, value)

    if opportunity_score is not None:
        for key in ("market", "idea_market"):
            value = (opportunity_score.components or {}).get(key)
            if isinstance(value, (int, float)):
                components[key] = value

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
        lifecycle_stage=lifecycle_stage,
        sla=sla,
    )


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def _candidate_rubric_filter() -> Any:
    return ScoreSnapshot.subject_type == "person"


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


async def _fetch_opportunity_scores(
    session: AsyncSession,
    person_ids: list[uuid.UUID],
) -> dict[uuid.UUID, ScoreSnapshot]:
    """Return the latest canonical opportunity-axis score per current opportunity."""
    if not person_ids:
        return {}

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
        select(OpportunityFounder.person_id, ScoreSnapshot)
        .select_from(OpportunityFounder)
        .join(Opportunity, Opportunity.id == OpportunityFounder.opportunity_id)
        .join(ScoreSnapshot, ScoreSnapshot.subject_id == Opportunity.id)
        .join(
            latest_opp,
            (OpportunityFounder.person_id == latest_opp.c.person_id)
            & (Opportunity.created_at == latest_opp.c.max_created),
        )
        .where(
            ScoreSnapshot.subject_type == "opportunity",
            ScoreSnapshot.rubric_version == "opportunity-axes-v1",
        )
        .order_by(ScoreSnapshot.created_at.desc())
    )
    grouped: dict[uuid.UUID, ScoreSnapshot] = {}
    for person_id, snapshot in result.tuples().all():
        grouped.setdefault(person_id, snapshot)
    return grouped


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


def _latest_opportunity_rows(person_ids: list[uuid.UUID] | None = None) -> Any:
    """Select one deterministic, newest opportunity row per person."""
    row_number = func.row_number().over(
        partition_by=OpportunityFounder.person_id,
        order_by=(Opportunity.created_at.desc(), Opportunity.id.desc()),
    ).label("row_number")
    query = (
        select(
            OpportunityFounder.person_id.label("person_id"),
            Opportunity.source_kind.label("source_kind"),
            Opportunity.company_name.label("company_name"),
            Opportunity.lifecycle_state.label("lifecycle_state"),
            Opportunity.received_at.label("received_at"),
            Opportunity.decision_due_at.label("decision_due_at"),
            Opportunity.stage_deadlines.label("stage_deadlines"),
            Opportunity.sla_owner.label("sla_owner"),
            Opportunity.sla_pause_reason.label("sla_pause_reason"),
            Opportunity.sla_attainment.label("sla_attainment"),
            row_number,
        )
        .select_from(OpportunityFounder)
        .join(Opportunity, Opportunity.id == OpportunityFounder.opportunity_id)
    )
    return query.where(OpportunityFounder.person_id.in_(person_ids)) if person_ids else query


async def _fetch_origin(
    session: AsyncSession,
    person_ids: list[uuid.UUID],
) -> dict[uuid.UUID, str]:
    """Return the source_kind of the most recent Opportunity per person."""
    if not person_ids:
        return {}

    latest_opp = _latest_opportunity_rows(person_ids).subquery()

    result = await session.execute(
        select(
            latest_opp.c.person_id,
            latest_opp.c.source_kind,
        )
        .where(latest_opp.c.row_number == 1)
    )
    return {row.person_id: row.source_kind for row in result}


async def _fetch_lifecycle_stages(
    session: AsyncSession,
    person_ids: list[uuid.UUID],
) -> dict[uuid.UUID, str]:
    """Return the lifecycle_state of the latest Opportunity per person."""
    if not person_ids:
        return {}

    latest_opp = _latest_opportunity_rows(person_ids).subquery()

    result = await session.execute(
        select(
            latest_opp.c.person_id,
            latest_opp.c.lifecycle_state,
        )
        .where(latest_opp.c.row_number == 1)
    )
    return {row.person_id: row.lifecycle_state for row in result}


def _sla_response(opportunity: Opportunity) -> CandidateSLAResponse:
    """Map an opportunity's persisted clock fields to the API contract."""
    return CandidateSLAResponse.model_validate(
        evaluate_sla(
            lifecycle_state=opportunity.lifecycle_state,
            received_at=opportunity.received_at,
            decision_due_at=opportunity.decision_due_at,
            stage_deadlines=opportunity.stage_deadlines,
            sla_owner=opportunity.sla_owner,
            sla_pause_reason=opportunity.sla_pause_reason,
            sla_attainment=opportunity.sla_attainment,
        )
    )


async def _fetch_sla_statuses(
    session: AsyncSession,
    person_ids: list[uuid.UUID],
) -> dict[uuid.UUID, CandidateSLAResponse]:
    """Return current SLA status for each person's latest opportunity."""
    if not person_ids:
        return {}
    latest_opp = _latest_opportunity_rows(person_ids).subquery()
    result = await session.execute(
        select(
            latest_opp.c.person_id,
            latest_opp.c.lifecycle_state,
            latest_opp.c.received_at,
            latest_opp.c.decision_due_at,
            latest_opp.c.stage_deadlines,
            latest_opp.c.sla_owner,
            latest_opp.c.sla_pause_reason,
            latest_opp.c.sla_attainment,
        ).where(latest_opp.c.row_number == 1)
    )
    statuses: dict[uuid.UUID, CandidateSLAResponse] = {}
    for row in result:
        statuses[row.person_id] = CandidateSLAResponse.model_validate(
            evaluate_sla(
                lifecycle_state=row.lifecycle_state,
                received_at=row.received_at,
                decision_due_at=row.decision_due_at,
                stage_deadlines=row.stage_deadlines,
                sla_owner=row.sla_owner,
                sla_pause_reason=row.sla_pause_reason,
                sla_attainment=row.sla_attainment,
            )
        )
    return statuses


def _normalize_search(value: str | None) -> str | None:
    """Normalize user search input once so cursors remain filter-stable."""
    normalized = " ".join((value or "").split()).casefold()
    return normalized or None


def _cursor_fingerprint(
    *, origin: str | None, stage: LifecycleStage | None, search: str | None
) -> str:
    payload = json.dumps(
        {"origin": origin, "stage": str(stage) if stage else None, "search": search},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def _encode_candidate_cursor(
    person: Person,
    *,
    origin: str | None,
    stage: LifecycleStage | None,
    search: str | None,
) -> str:
    if person.created_at is None:
        raise RuntimeError("Candidate cursor requires a creation timestamp")
    payload = {
        "created_at": person.created_at.isoformat(),
        "id": str(person.id),
        "fingerprint": _cursor_fingerprint(origin=origin, stage=stage, search=search),
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode())
    return encoded.decode().rstrip("=")


def _decode_candidate_cursor(
    cursor: str,
    *,
    origin: str | None,
    stage: LifecycleStage | None,
    search: str | None,
) -> tuple[datetime, uuid.UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        created_at = datetime.fromisoformat(str(payload["created_at"]))
        person_id = uuid.UUID(str(payload["id"]))
        fingerprint = str(payload["fingerprint"])
    except (
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        binascii.Error,
    ):
        raise HTTPException(status_code=400, detail="Invalid candidate cursor") from None

    if fingerprint != _cursor_fingerprint(origin=origin, stage=stage, search=search):
        raise HTTPException(status_code=400, detail="Candidate cursor does not match filters")
    return created_at, person_id


def _candidate_query(
    *,
    origin: str | None,
    stage: LifecycleStage | None,
    search: str | None,
    cursor: tuple[datetime, uuid.UUID] | None,
) -> Any:
    """Build one canonical candidate query used for both rows and totals."""
    query = select(Person).where(Person.canonical.is_(True))

    latest_opp: Any | None = None
    if origin or stage or search:
        latest_opp = _latest_opportunity_rows().subquery()
        join_method = query.join if (origin or stage) else query.outerjoin
        query = join_method(
            latest_opp,
            (Person.id == latest_opp.c.person_id) & (latest_opp.c.row_number == 1),
        )
        if origin:
            query = query.where(latest_opp.c.source_kind == origin)
        if stage:
            query = query.where(latest_opp.c.lifecycle_state == stage)

    if search:
        like = f"%{search}%"
        assert latest_opp is not None
        observation_match = (
            select(Observation.id)
            .join(SourceSnapshot, SourceSnapshot.id == Observation.snapshot_id)
            .where(
                Observation.subject_id == Person.id,
                or_(
                    func.lower(Observation.object_value).like(like),
                    func.lower(Observation.predicate).like(like),
                    func.lower(SourceSnapshot.source_type).like(like),
                    func.lower(SourceSnapshot.uri).like(like),
                ),
            )
            .exists()
        )
        query = query.where(
            or_(
                func.lower(Person.display_name).like(like),
                func.lower(Person.stable_id).like(like),
                func.lower(Person.email).like(like),
                func.lower(cast(Person.handles, String)).like(like),
                func.lower(latest_opp.c.company_name).like(like),
                observation_match,
            )
        )

    if cursor:
        created_at, person_id = cursor
        query = query.where(
            or_(
                Person.created_at < created_at,
                (Person.created_at == created_at) & (Person.id < person_id),
            )
        )

    return query.order_by(Person.created_at.desc(), Person.id.desc())


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=list[CandidateResponse] | CandidateListResponse)
async def list_candidates(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(
        default=None, description="Opaque cursor from a previous v1 response"
    ),
    search: str | None = Query(
        default=None,
        max_length=200,
        description="Case-insensitive search across identity and evidence fields",
    ),
    q: str | None = Query(default=None, max_length=200, description="Alias for search"),
    version: Literal["1", "v1"] | None = Query(
        default=None,
        description="Request the versioned envelope (also available via Accept header)",
    ),
    origin: str | None = Query(
        default=None,
        pattern=r"^(inbound|outbound)$",
        description="Filter by opportunity origin (inbound/outbound)",
    ),
    stage: Annotated[
        LifecycleStage | None,
        Query(description="Filter by lifecycle stage (e.g. investigating, memo_ready, contacted)"),
    ] = None,
    accept: Annotated[str | None, Header()] = None,
) -> list[CandidateResponse] | CandidateListResponse:
    """List sourcing candidates with canonical filters and cursor pagination.

    Returns persons ordered by creation date and ID (newest first with a
    deterministic tie-break). Origin and stage filters use the same latest
    opportunity row; search is evaluated against identity, current company,
    and provenance-backed observation fields. Scores are populated from the
    latest ScoreSnapshot with a founder-score rubric, if one exists. Legacy
    callers receive an array; v1 callers receive the envelope and total count.
    """
    normalized_search = _normalize_search(search if search is not None else q)
    decoded_cursor = _decode_candidate_cursor(
        cursor,
        origin=origin,
        stage=stage,
        search=normalized_search,
    ) if cursor else None
    query = _candidate_query(
        origin=origin,
        stage=stage,
        search=normalized_search,
        cursor=decoded_cursor,
    )
    envelope_requested = bool(
        version in {"1", "v1"}
        or (accept and "application/vnd.the-vc-brain.candidates.v1+json" in accept)
    )

    # Count against the same canonical filters, independent of the cursor.
    total_query = _candidate_query(
        origin=origin,
        stage=stage,
        search=normalized_search,
        cursor=None,
    ).order_by(None)
    total_result = await session.execute(
        select(func.count()).select_from(total_query.subquery())
    )
    total_count = int(total_result.scalar_one())

    # Fetch one extra row to determine whether a continuation exists.
    query = query.limit(limit + 1)

    result = await session.execute(query)
    persons: list[Person] = list(result.scalars().all())
    has_next = len(persons) > limit
    persons = persons[:limit]

    if not persons:
        if envelope_requested:
            return CandidateListResponse(
                items=[],
                next_cursor=None,
                total_count=total_count,
                limit=limit,
                search=normalized_search,
                filters={
                    key: value
                    for key, value in {"origin": origin, "stage": stage}.items()
                    if value
                },
            )
        return []

    person_ids = [p.id for p in persons]

    # Batch-fetch latest scores, origins, and lifecycle stages
    score_snapshots = await _fetch_score_snapshots(session, person_ids)
    origins = await _fetch_origin(session, person_ids)
    profiles = await _fetch_candidate_profiles(session, person_ids)
    lifecycle_stages = await _fetch_lifecycle_stages(session, person_ids)
    opportunity_scores = await _fetch_opportunity_scores(session, person_ids)
    sla_statuses = await _fetch_sla_statuses(session, person_ids)

    items = [
        map_person_to_candidate(
            person=p,
            origin=origins.get(p.id) or ("outbound" if p.handles else None),
            score_snapshots=score_snapshots.get(p.id),
            opportunity_score=opportunity_scores.get(p.id),
            profile=profiles.get(p.id),
            lifecycle_stage=lifecycle_stages.get(p.id),
            sla=sla_statuses.get(p.id),
        )
        for p in persons
    ]
    if not envelope_requested:
        return items

    next_cursor = (
        _encode_candidate_cursor(
            persons[-1],
            origin=origin,
            stage=stage,
            search=normalized_search,
        )
        if has_next
        else None
    )
    return CandidateListResponse(
        items=items,
        next_cursor=next_cursor,
        total_count=total_count,
        limit=limit,
        search=normalized_search,
        filters={key: value for key, value in {"origin": origin, "stage": stage}.items() if value},
    )


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
    opportunity_scores = await _fetch_opportunity_scores(session, [person.id])
    origins = await _fetch_origin(session, [person.id])
    profiles = await _fetch_candidate_profiles(session, [person.id])
    lifecycle_stages = await _fetch_lifecycle_stages(session, [person.id])
    candidate = map_person_to_candidate(
        person,
        origin=origins.get(person.id) or ("outbound" if person.handles else None),
        score_snapshots=score_snapshots.get(person.id),
        opportunity_score=opportunity_scores.get(person.id),
        profile=profiles.get(person.id),
        lifecycle_stage=lifecycle_stages.get(person.id),
    )

    opportunity_result = await session.execute(
        select(Opportunity)
        .join(OpportunityFounder, OpportunityFounder.opportunity_id == Opportunity.id)
        .where(OpportunityFounder.person_id == person.id)
        .order_by(Opportunity.created_at.desc())
        .limit(1)
    )
    opportunity = opportunity_result.scalar_one_or_none()
    decision_proposal: CandidateDecisionProposalResponse | None = None
    if opportunity is not None:
        candidate = candidate.model_copy(update={"sla": _sla_response(opportunity)})
        proposal_result = await session.execute(
            select(DecisionProposal)
            .where(DecisionProposal.opportunity_id == opportunity.id)
            .order_by(DecisionProposal.created_at.desc())
            .limit(1)
        )
        proposal = proposal_result.scalar_one_or_none()
        if proposal is not None:
            decision_proposal = CandidateDecisionProposalResponse.model_validate(proposal)

    observation_result = await session.execute(
        select(Observation, SourceSnapshot)
        .join(SourceSnapshot, SourceSnapshot.id == Observation.snapshot_id)
        .where(Observation.subject_id == person.id)
        .order_by(Observation.observed_at.desc())
        .limit(200)
    )
    observations = [
        CandidateObservationResponse(
            id=observation.id,
            predicate=observation.predicate,
            object_value=observation.object_value,
            confidence=observation.confidence,
            source_locator=observation.source_locator,
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
            id=claim.id,
            predicate=claim.predicate,
            object_value=claim.object_value,
            status=claim.status,
            confidence=claim.confidence,
            trust_score=claim.trust_score,
            trust_interval=claim.trust_interval,
            trust_components=claim.trust_components,
            trust_explanation=claim.trust_explanation,
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
                organization_id=opportunity.organization_id,
                company_name=opportunity.company_name,
                source_kind=opportunity.source_kind,
                lifecycle_state=opportunity.lifecycle_state,
                thesis_version=opportunity.thesis_version,
                created_at=opportunity.created_at,
            )
            if opportunity is not None
            else None
        ),
        decision_proposal=decision_proposal,
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
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> CandidateDecisionResponse:
    """Persist an idempotent, lifecycle-validated human VC decision."""
    idempotency_key = idempotency_key.strip()
    if not 1 <= len(idempotency_key) <= 128:
        raise HTTPException(status_code=422, detail="Idempotency-Key must be 1-128 characters")

    person = await session.get(Person, candidate_id)
    if person is None or not person.canonical:
        raise HTTPException(status_code=404, detail="Candidate not found")

    opportunity_result = await session.execute(
        select(Opportunity)
        .join(OpportunityFounder, OpportunityFounder.opportunity_id == Opportunity.id)
        .where(
            Opportunity.id == payload.opportunity_id,
            OpportunityFounder.person_id == person.id,
        )
        .with_for_update(of=Opportunity)
    )
    opportunity = opportunity_result.scalar_one_or_none()
    if opportunity is None:
        raise HTTPException(status_code=409, detail="Candidate is not linked to this opportunity")

    reason = payload.reason.strip()
    if len(reason) < 3:
        raise HTTPException(status_code=422, detail="Decision reason must be at least 3 characters")

    existing_result = await session.execute(
        select(DecisionEvent).where(DecisionEvent.idempotency_key == idempotency_key)
    )
    existing_event = existing_result.scalar_one_or_none()
    if existing_event is not None:
        existing_action = (
            existing_event.sla_metadata.get("action")
            if isinstance(existing_event.sla_metadata, dict)
            else None
        )
        if (
            existing_event.opportunity_id != opportunity.id
            or existing_action != payload.action
            or existing_event.reason != reason
        ):
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key was already used for another decision",
            )
        return CandidateDecisionResponse(
            event_id=existing_event.id,
            prior_state=existing_event.prior_state,
            new_state=existing_event.new_state,
            action=payload.action,
            reason=reason,
            created_at=existing_event.created_at,
        )

    prior_state = opportunity.lifecycle_state
    new_state = decision_state_for_action(payload.action)
    if not is_valid_transition(prior_state, new_state) or prior_state == new_state:
        raise HTTPException(
            status_code=409,
            detail=f"Decision is not allowed from lifecycle state '{prior_state}'",
        )

    memo_result = await session.execute(
        select(InvestmentMemo)
        .where(
            InvestmentMemo.opportunity_id == opportunity.id,
            InvestmentMemo.status == "succeeded",
        )
        .order_by(InvestmentMemo.created_at.desc())
        .limit(1)
    )
    memo = memo_result.scalar_one_or_none()
    if memo is None:
        raise HTTPException(status_code=409, detail="A validated memo is required before deciding")

    proposal_result = await session.execute(
        select(DecisionProposal)
        .where(DecisionProposal.opportunity_id == opportunity.id)
        .order_by(DecisionProposal.created_at.desc())
        .limit(1)
    )
    proposal = proposal_result.scalar_one_or_none()

    decision_at = datetime.now(UTC)
    sla = finalize_sla(opportunity, decision_at)
    event = DecisionEvent(
        opportunity_id=opportunity.id,
        prior_state=prior_state,
        new_state=new_state,
        actor="vc-ui:unattributed",
        idempotency_key=idempotency_key,
        reason=reason,
        sla_metadata={
            "action": payload.action,
            "source": "decision-floating-dock",
            "memo_id": str(memo.id),
            "claim_ids": memo.claim_ids,
            "assessment_ids": memo.assessment_ids,
            "thesis_version": memo.thesis_version,
            "sla_attainment": sla["attainment"],
            "sla_status": sla["status"],
            "decision_at": decision_at.isoformat(),
            "proposal_id": str(proposal.id) if proposal is not None else None,
        },
    )
    if proposal is not None:
        proposed_action = {"proceed": "invest", "hold": "hold", "decline": "decline"}[
            payload.action
        ]
        proposal.override_reason = (
            reason if proposed_action != proposal.action else None
        )
        proposal.action = proposed_action
        proposal.status = "overridden" if proposal.override_reason else "approved"
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


@router.post("/{candidate_id}/feedback", response_model=CandidateFeedbackResponse)
async def record_candidate_feedback(
    candidate_id: uuid.UUID,
    payload: CandidateFeedbackRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CandidateFeedbackResponse:
    """Persist analyst workflow feedback separately from investment outcomes."""
    person = await session.get(Person, candidate_id)
    if person is None or not person.canonical:
        raise HTTPException(status_code=404, detail="Candidate not found")
    feedback = CandidateFeedback(
        person_id=person.id,
        action=payload.action,
        reason=payload.reason.strip(),
        actor="vc-ui:unattributed",
    )
    session.add(feedback)
    await session.commit()
    return CandidateFeedbackResponse(
        id=feedback.id,
        person_id=feedback.person_id,
        action=payload.action,
        reason=feedback.reason,
        actor=feedback.actor,
        created_at=feedback.created_at,
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
    ai_policy = external_ai_use_decision(person, "outreach")
    external_api_key = settings.llm_api_key if ai_policy.allowed else ""
    draft = await draft_outreach_email(
        founder_name=person.display_name or "Founder",
        company=company,
        email_type=payload.email_type,
        brief=payload.brief.strip(),
        evidence_summary=redact_direct_identifiers(
            "\n".join(item for item in evidence_parts if item)
        ),
        api_key=external_api_key,
        model=settings.llm_model,
    )
    if settings.llm_api_key and not ai_policy.allowed:
        draft.warning = (
            "External AI drafting was blocked by privacy policy; a local template was used."
        )
    return OutreachDraftResponse(
        **draft.model_dump(),
        recipient_email=person.email,
    )


@router.post(
    "/{candidate_id}/outreach/{outreach_id}/approve",
    response_model=OutreachActionResponse,
)
async def approve_outreach(
    candidate_id: uuid.UUID,
    outreach_id: uuid.UUID,
    payload: OutreachApprovalRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OutreachActionResponse:
    """Approve one persisted draft after rechecking recipient suppression."""
    from app.outreach_delivery import contact_block_reason

    message = await session.get(OutreachMessage, outreach_id)
    if message is None or message.person_id != candidate_id:
        raise HTTPException(status_code=404, detail="Outreach draft not found")
    if message.status != "drafted":
        raise HTTPException(status_code=409, detail=f"Outreach is already {message.status}")
    person = await session.get(Person, candidate_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    block_reason = contact_block_reason(person)
    if block_reason:
        message.status = "opted_out" if block_reason.startswith("suppressed_") else "failed"
        message.failure_reason = block_reason
        await session.commit()
        raise HTTPException(status_code=409, detail=block_reason)

    message.status = "approved"
    message.approved_by = payload.approved_by.strip()
    message.approved_at = datetime.now(UTC)
    await session.commit()
    return OutreachActionResponse(
        outreach_id=message.id,
        status=message.status,
        recipient_email=message.recipient_email,
        detail="Draft approved; sending still requires an explicit request.",
    )


@router.post(
    "/{candidate_id}/outreach/{outreach_id}/send",
    response_model=OutreachActionResponse,
)
async def request_outreach_send(
    candidate_id: uuid.UUID,
    outreach_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OutreachActionResponse:
    """Record a send request without simulating provider delivery."""
    message = await session.get(OutreachMessage, outreach_id)
    if message is None or message.person_id != candidate_id:
        raise HTTPException(status_code=404, detail="Outreach draft not found")
    if message.status != "approved":
        raise HTTPException(status_code=409, detail="Outreach must be approved before sending")
    message.status = "send_requested"
    message.requested_at = datetime.now(UTC)
    await session.commit()
    return OutreachActionResponse(
        outreach_id=message.id,
        status=message.status,
        recipient_email=message.recipient_email,
        detail="Send requested; status changes to sent only after provider confirmation.",
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
# Manual contact endpoint
# ---------------------------------------------------------------------------


@router.post("/{candidate_id}/contact", response_model=dict[str, str])
async def contact_candidate(
    candidate_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """Manually trigger cold outreach for a candidate.

    Works regardless of contact_threshold — allows investors to manually
    target investigated persons who were not auto-contacted.
    """
    person = await session.get(Person, candidate_id)
    if person is None or not person.canonical:
        raise HTTPException(status_code=404, detail="Candidate not found")

    from app.collectors.queue import enqueue as queue_enqueue

    async with redis_connection() as redis:
        await queue_enqueue(
            redis,
            {"job_type": "contact_outbound", "person_id": str(person.id)},
            priority=10.0,
        )

    return {"message": f"Outreach queued for {candidate_id}"}


# ---------------------------------------------------------------------------
# Investment memo routes
# ---------------------------------------------------------------------------


class MemoResponse(BaseModel):
    """A generated investment memo."""

    sections: list[dict[str, object]]
    status: Literal["pending", "failed", "degraded", "succeeded"]
    generation_mode: str | None = None
    model_version: str | None = None
    created_at: datetime | None = None


class MemoGenerationRequest(BaseModel):
    opportunity_id: uuid.UUID


@router.get("/{candidate_id}/memo", response_model=MemoResponse)
async def get_candidate_memo(
    candidate_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    opportunity_id: Annotated[
        uuid.UUID,
        Query(description="Exact opportunity whose memo is requested"),
    ],
) -> MemoResponse:
    """Return the latest investment memo for a candidate."""
    from app.db.models import InvestmentMemo

    result = await session.execute(
        select(InvestmentMemo)
        .join(Opportunity, Opportunity.id == InvestmentMemo.opportunity_id)
        .join(OpportunityFounder, OpportunityFounder.opportunity_id == Opportunity.id)
        .where(
            OpportunityFounder.person_id == candidate_id,
            InvestmentMemo.opportunity_id == opportunity_id,
        )
        .order_by(InvestmentMemo.created_at.desc())
        .limit(1)
    )
    memo = result.scalar_one_or_none()
    if memo is None:
        raise HTTPException(status_code=404, detail="No memo found for this candidate")

    sections = memo.sections.get("sections", []) if isinstance(memo.sections, dict) else []
    return MemoResponse(
        sections=sections,
        status=memo.status,
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
    payload: MemoGenerationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """Queue investment memo generation for a candidate."""
    person = await session.get(Person, candidate_id)
    if person is None or not person.canonical:
        raise HTTPException(status_code=404, detail="Candidate not found")

    opportunity_result = await session.execute(
        select(Opportunity)
        .join(OpportunityFounder, OpportunityFounder.opportunity_id == Opportunity.id)
        .where(
            Opportunity.id == payload.opportunity_id,
            OpportunityFounder.person_id == person.id,
        )
    )
    if opportunity_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=409, detail="Candidate is not linked to this opportunity")

    from app.collectors.queue import enqueue as queue_enqueue

    async with redis_connection() as redis:
        # Acquire the request-scoped pool before committing the durable queue
        # row. A connection-construction failure must not orphan a queued job.
        job = await create_job(session, "generate_memo")
        await session.commit()
        try:
            await queue_enqueue(
                redis,
                {
                    "job_type": "generate_memo",
                    "person_id": str(person.id),
                    "opportunity_id": str(payload.opportunity_id),
                    "job_id": str(job.id),
                },
                priority=10.0,
            )
        except Exception as exc:
            await update_job(
                session,
                job.id,
                status="failed",
                phase="queue",
                last_error=str(exc),
                result={"error": "queue_failed"},
            )
            await session.commit()
            raise HTTPException(status_code=503, detail="Unable to queue memo job") from exc

    return {"job_id": str(job.id), "message": f"Memo generation queued for {candidate_id}"}
