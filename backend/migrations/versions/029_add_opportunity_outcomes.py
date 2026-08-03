"""add append-only outcome records

Revision ID: 029
Revises: 028
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "029"
down_revision: str | None = "028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "opportunity_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("outcome_domain", sa.String(length=32), nullable=False),
        sa.Column("outcome_type", sa.String(length=64), nullable=False),
        sa.Column(
            "outcome_value", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=True),
        sa.Column("censoring", sa.String(length=32), nullable=False, server_default="observed"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column(
            "provenance", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opportunity_outcomes_opportunity_id",
        "opportunity_outcomes",
        ["opportunity_id"],
    )
    op.create_index(
        "ix_opportunity_outcomes_outcome_domain",
        "opportunity_outcomes",
        ["outcome_domain"],
    )
    op.create_index(
        "ix_opportunity_outcomes_outcome_type",
        "opportunity_outcomes",
        ["outcome_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_opportunity_outcomes_outcome_type", table_name="opportunity_outcomes")
    op.drop_index("ix_opportunity_outcomes_outcome_domain", table_name="opportunity_outcomes")
    op.drop_index("ix_opportunity_outcomes_opportunity_id", table_name="opportunity_outcomes")
    op.drop_table("opportunity_outcomes")
