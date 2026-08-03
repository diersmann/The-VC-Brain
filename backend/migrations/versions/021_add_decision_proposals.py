"""persist structured decision proposals and readiness snapshots

Revision ID: 021
Revises: 020
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "021"
down_revision: str | None = "020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "memo_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investment_memos.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=24), nullable=False),
        sa.Column("check_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("ownership_target", sa.Numeric(6, 3), nullable=True),
        sa.Column("conviction", sa.String(length=16), nullable=True),
        sa.Column(
            "founder_assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "market_assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "idea_market_assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "top_evidence", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "top_risks", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "open_conditions",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "readiness_blockers",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "readiness_status", sa.String(length=16), nullable=False, server_default="blocked"
        ),
        sa.Column("thesis_version", sa.String(length=64), nullable=True),
        sa.Column(
            "rubric_versions",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("memo_model_version", sa.String(length=64), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "action IN ('invest','hold','investigate','decline')",
            name="ck_decision_proposals_action",
        ),
        sa.CheckConstraint(
            "status IN ('draft','approved','overridden')",
            name="ck_decision_proposals_status",
        ),
        sa.CheckConstraint(
            "readiness_status IN ('ready','blocked')",
            name="ck_decision_proposals_readiness_status",
        ),
    )
    op.create_index(
        "ix_decision_proposals_opportunity_id", "decision_proposals", ["opportunity_id"]
    )
    op.create_index("ix_decision_proposals_memo_id", "decision_proposals", ["memo_id"])


def downgrade() -> None:
    op.drop_index("ix_decision_proposals_memo_id", table_name="decision_proposals")
    op.drop_index("ix_decision_proposals_opportunity_id", table_name="decision_proposals")
    op.drop_table("decision_proposals")
