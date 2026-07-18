"""create core entities

Revision ID: 001
Revises:
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # -----------------------------------------------------------------------
    # Persons
    # -----------------------------------------------------------------------
    op.create_table(
        "persons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("stable_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("display_name", sa.String(512), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("handles", postgresql.JSONB, nullable=True),
        sa.Column("consent_state", sa.String(32), nullable=False, server_default="pending"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # -----------------------------------------------------------------------
    # Organizations
    # -----------------------------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("stable_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("org_type", sa.String(64), nullable=False, server_default="company"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # -----------------------------------------------------------------------
    # Opportunities
    # -----------------------------------------------------------------------
    op.create_table(
        "opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_name", sa.String(512), nullable=False),
        sa.Column("source_kind", sa.String(32), nullable=False, server_default="inbound"),
        sa.Column("lifecycle_state", sa.String(32), nullable=False, server_default="received"),
        sa.Column("thesis_version", sa.String(64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # -----------------------------------------------------------------------
    # Opportunity-Founder join table
    # -----------------------------------------------------------------------
    op.create_table(
        "opportunity_founders",
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("persons.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    # -----------------------------------------------------------------------
    # Source Snapshots
    # -----------------------------------------------------------------------
    op.create_table(
        "source_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("uri", sa.Text, nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False, server_default="webpage"),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("storage_path", sa.Text, nullable=False),
        sa.Column("license_metadata", postgresql.JSONB, nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # -----------------------------------------------------------------------
    # Observations
    # -----------------------------------------------------------------------
    op.create_table(
        "observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("predicate", sa.String(128), nullable=False),
        sa.Column("object_value", sa.Text, nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extractor_version", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # -----------------------------------------------------------------------
    # Claims
    # -----------------------------------------------------------------------
    op.create_table(
        "claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("observation_ids", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("predicate", sa.String(128), nullable=False),
        sa.Column("object_value", sa.Text, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="unverified"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("valid_time_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_time_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "supersession_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("claims.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # -----------------------------------------------------------------------
    # Relationships
    # -----------------------------------------------------------------------
    op.create_table(
        "relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "person_a_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("persons.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "person_b_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("persons.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("relationship_type", sa.String(32), nullable=False),
        sa.Column("evidence", postgresql.JSONB, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_relationships_pair", "relationships", ["person_a_id", "person_b_id"])

    # -----------------------------------------------------------------------
    # Score Snapshots
    # -----------------------------------------------------------------------
    op.create_table(
        "score_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("rubric_version", sa.String(64), nullable=False),
        sa.Column("components", postgresql.JSONB, nullable=False),
        sa.Column("confidence_interval", postgresql.JSONB, nullable=True),
        sa.Column("evidence_ids", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # -----------------------------------------------------------------------
    # Assessments
    # -----------------------------------------------------------------------
    op.create_table(
        "assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("axis", sa.String(32), nullable=False),
        sa.Column("rating", sa.String(16), nullable=False),
        sa.Column("trend", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("evidence_ids", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("counter_evidence_ids", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("unknowns", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # -----------------------------------------------------------------------
    # Decision Events
    # -----------------------------------------------------------------------
    op.create_table(
        "decision_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("prior_state", sa.String(32), nullable=False),
        sa.Column("new_state", sa.String(32), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("sla_metadata", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("decision_events")
    op.drop_table("assessments")
    op.drop_table("score_snapshots")
    op.drop_index("ix_relationships_pair", table_name="relationships")
    op.drop_table("relationships")
    op.drop_table("claims")
    op.drop_table("observations")
    op.drop_table("source_snapshots")
    op.drop_table("opportunity_founders")
    op.drop_table("opportunities")
    op.drop_table("organizations")
    op.drop_table("persons")
