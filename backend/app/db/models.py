"""SQLAlchemy ORM models for The VC Brain.

All core entities, relationships, and audit/log tables.
"""

import uuid
from datetime import datetime
from decimal import Decimal

# pgvector for embedding storage
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    LargeBinary,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# ---------------------------------------------------------------------------
# Helper: auto-generating UUID primary key + created_at / updated_at
# ---------------------------------------------------------------------------


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _utcnow() -> datetime:
    return datetime.utcnow()


class TimestampMixin:
    """Mixin that adds created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# Persons
# ---------------------------------------------------------------------------


class Person(TimestampMixin, Base):
    __tablename__ = "persons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    stable_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    handles: Mapped[dict[str, str] | None] = mapped_column(JSONB, nullable=True)
    consent_state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    privacy_legal_basis: Mapped[str | None] = mapped_column(String(64), nullable=True)
    privacy_notice_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    privacy_purposes: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, default=dict)
    privacy_provider_policy_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    privacy_retention_days: Mapped[int | None] = mapped_column(nullable=True)
    privacy_residency: Mapped[str | None] = mapped_column(String(64), nullable=True)
    avatar_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    avatar_mime_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    avatar_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    avatar_source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    avatar_source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Identity / supersession
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    canonical: Mapped[bool] = mapped_column(nullable=False, default=True)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # relationships
    opportunities: Mapped[list["Opportunity"]] = relationship(
        secondary="opportunity_founders", back_populates="founders"
    )
    relationships_a: Mapped[list["Relationship"]] = relationship(
        foreign_keys="[Relationship.person_a_id]", back_populates="person_a"
    )
    relationships_b: Mapped[list["Relationship"]] = relationship(
        foreign_keys="[Relationship.person_b_id]", back_populates="person_b"
    )
    superseded_by: Mapped["Person | None"] = relationship(
        foreign_keys=[superseded_by_id],
        remote_side="Person.id",
        back_populates="supersedes",
    )
    supersedes: Mapped[list["Person"]] = relationship(
        foreign_keys=[superseded_by_id],
        back_populates="superseded_by",
    )


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    stable_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    org_type: Mapped[str] = mapped_column(String(64), nullable=False, default="company")


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------


class Opportunity(TimestampMixin, Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        CheckConstraint(
            "lifecycle_state IN ("
            "'discovered','interesting','investigating','contacted','received',"
            "'memo_ready','hold','approved','closed','screening','triage','diligence')",
            name="ck_opportunities_lifecycle_state",
        ),
        CheckConstraint(
            "sla_attainment IN ('pending','met','breached')",
            name="ck_opportunities_sla_attainment",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    company_name: Mapped[str] = mapped_column(String(512), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="inbound")
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False, default="received")
    thesis_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stage_deadlines: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    sla_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sla_pause_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sla_attainment: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    sla_decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # relationships
    founders: Mapped[list["Person"]] = relationship(
        secondary="opportunity_founders", back_populates="opportunities"
    )
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="opportunity")
    decision_events: Mapped[list["DecisionEvent"]] = relationship(back_populates="opportunity")


# Many-to-many join table
class OpportunityFounder(Base):
    __tablename__ = "opportunity_founders"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        primary_key=True,
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        primary_key=True,
    )


# ---------------------------------------------------------------------------
# Investment theses
# ---------------------------------------------------------------------------


class InvestmentThesis(TimestampMixin, Base):
    """Immutable, versioned investor mandate used for opportunity alignment."""

    __tablename__ = "investment_theses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    version: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    stages: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    sectors: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    excluded_sectors: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    regions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    check_size_min_k_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_size_max_k_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    ownership_target_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_appetite: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced")
    scoring_weights: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    discovery_queries: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    source_freshness_days: Mapped[dict[str, int]] = mapped_column(
        JSONB, nullable=False, default=dict
    )


# ---------------------------------------------------------------------------
# Source Snapshots (raw collected material)
# ---------------------------------------------------------------------------


class SourceSnapshot(TimestampMixin, Base):
    __tablename__ = "source_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="webpage")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    license_metadata: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    observations: Mapped[list["Observation"]] = relationship(back_populates="snapshot")


# ---------------------------------------------------------------------------
# Inbound submissions and durable outbox
# ---------------------------------------------------------------------------


class InboundSubmission(TimestampMixin, Base):
    """Idempotent application envelope linking a deck to its opportunity."""

    __tablename__ = "inbound_submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    idempotency_key: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="RESTRICT"), nullable=False
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="accepted")


class OutboxEvent(TimestampMixin, Base):
    """Durable event dispatched to Redis after its database transaction commits."""

    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    dedupe_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Durable job ledger
# ---------------------------------------------------------------------------


class JobRun(TimestampMixin, Base):
    """Durable lifecycle record for an asynchronous worker job."""

    __tablename__ = "job_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued", index=True)
    phase: Mapped[str] = mapped_column(String(64), nullable=False, default="queued")
    attempt: Mapped[int] = mapped_column(nullable=False, default=0)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(nullable=False, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CandidateFeedback(TimestampMixin, Base):
    """Append-only analyst feedback kept separate from investment outcomes."""

    __tablename__ = "candidate_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    feedback_metadata: Mapped[dict[str, object] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OutreachMessage(TimestampMixin, Base):
    """Human-reviewed outreach message and provider delivery state."""

    __tablename__ = "outreach_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="RESTRICT"), nullable=False
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False
    )
    recipient_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    subject: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    generation_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="template")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="drafted", index=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Observations (raw extractor output before reconciliation)
# ---------------------------------------------------------------------------


class Observation(TimestampMixin, Base):
    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    predicate: Mapped[str] = mapped_column(String(128), nullable=False)
    object_value: Mapped[str] = mapped_column(Text, nullable=False)
    source_locator: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    snapshot: Mapped["SourceSnapshot"] = relationship(back_populates="observations")


# ---------------------------------------------------------------------------
# Claims (reconciled, trusted facts)
# ---------------------------------------------------------------------------


class Claim(TimestampMixin, Base):
    __tablename__ = "claims"
    __table_args__ = (
        CheckConstraint(
            "status IN ('supported','contradicted','unverified','tavily_synthesized')",
            name="ck_claims_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    observation_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    predicate: Mapped[str] = mapped_column(String(128), nullable=False)
    object_value: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="unverified")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    trust_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    trust_interval: Mapped[dict[str, float] | None] = mapped_column(JSONB, nullable=True)
    trust_components: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    trust_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_time_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_time_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersession_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="SET NULL"),
        nullable=True,
    )


# ---------------------------------------------------------------------------
# Relationships (graph edges)
# ---------------------------------------------------------------------------


class Relationship(TimestampMixin, Base):
    __tablename__ = "relationships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    person_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    person_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    person_a: Mapped["Person"] = relationship(
        foreign_keys=[person_a_id], back_populates="relationships_a"
    )
    person_b: Mapped["Person"] = relationship(
        foreign_keys=[person_b_id], back_populates="relationships_b"
    )

    __table_args__ = (Index("ix_relationships_pair", "person_a_id", "person_b_id"),)


# ---------------------------------------------------------------------------
# Score Snapshots (versioned scorecard at a point in time)
# ---------------------------------------------------------------------------


class ScoreSnapshot(TimestampMixin, Base):
    __tablename__ = "score_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="person", index=True
    )
    rubric_version: Mapped[str] = mapped_column(String(64), nullable=False)
    components: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    confidence_interval: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    input_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    provenance: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)


# ---------------------------------------------------------------------------
# Assessments (per-opportunity, per-axis)
# ---------------------------------------------------------------------------


class Assessment(TimestampMixin, Base):
    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint(
            "axis IN ('Founder','Market','Idea-Market','execution','technical','commercial')",
            name="ck_assessments_axis",
        ),
        CheckConstraint(
            "rating IN ('Bullish','Neutral','Bearish','bullish','neutral','bearish')",
            name="ck_assessments_rating",
        ),
        CheckConstraint(
            "trend IN ('Improving','Stable','Declining','improving','stable','declining')",
            name="ck_assessments_trend",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    axis: Mapped[str] = mapped_column(String(32), nullable=False)
    rating: Mapped[str] = mapped_column(String(16), nullable=False)
    trend: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    counter_evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    unknowns: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    opportunity: Mapped["Opportunity"] = relationship(back_populates="assessments")


# ---------------------------------------------------------------------------
# Decision Events (append-only lifecycle audit log)
# ---------------------------------------------------------------------------


class DecisionEvent(TimestampMixin, Base):
    __tablename__ = "decision_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prior_state: Mapped[str] = mapped_column(String(32), nullable=False)
    new_state: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sla_metadata: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)

    opportunity: Mapped["Opportunity"] = relationship(back_populates="decision_events")


# ---------------------------------------------------------------------------
# Person Matches (identity resolution review queue)
# ---------------------------------------------------------------------------


class PersonMatch(TimestampMixin, Base):
    """A candidate pair of Persons that may represent the same real person.

    Created when identity resolution finds a match with confidence in the
    ambiguous band (0.5-0.8).  An investor can approve or reject the match.
    """

    __tablename__ = "person_matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    person_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    person_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasons: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    resolved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Investment Memos (generated from evidence + assessments)
# ---------------------------------------------------------------------------

class InvestmentMemo(TimestampMixin, Base):
    """Append-only investment memo generated by the memo agent."""

    __tablename__ = "investment_memos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    thesis_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    claim_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    assessment_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    sections: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)


# ---------------------------------------------------------------------------
# Decision proposals and readiness snapshots
# ---------------------------------------------------------------------------


class DecisionProposal(TimestampMixin, Base):
    """Versioned, evidence-backed proposal prepared for human review."""

    __tablename__ = "decision_proposals"
    __table_args__ = (
        CheckConstraint(
            "action IN ('invest','hold','investigate','decline')",
            name="ck_decision_proposals_action",
        ),
        CheckConstraint(
            "status IN ('draft','approved','overridden')",
            name="ck_decision_proposals_status",
        ),
        CheckConstraint(
            "readiness_status IN ('ready','blocked')",
            name="ck_decision_proposals_readiness_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investment_memos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    check_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    ownership_target: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    conviction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    founder_assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True
    )
    market_assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True
    )
    idea_market_assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True
    )
    top_evidence: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    top_risks: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    open_conditions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    readiness_blockers: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    readiness_status: Mapped[str] = mapped_column(String(16), nullable=False, default="blocked")
    thesis_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rubric_versions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    memo_model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
