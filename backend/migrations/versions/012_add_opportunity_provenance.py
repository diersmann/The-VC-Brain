"""add opportunity provenance to evidence and memo inputs

Revision ID: 012
Revises: 011
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "observations",
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index("ix_observations_opportunity_id", "observations", ["opportunity_id"])
    op.add_column(
        "claims",
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index("ix_claims_opportunity_id", "claims", ["opportunity_id"])
    op.add_column(
        "investment_memos",
        sa.Column("claim_ids", postgresql.JSONB, nullable=False, server_default="[]"),
    )
    op.add_column(
        "investment_memos",
        sa.Column("assessment_ids", postgresql.JSONB, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("investment_memos", "assessment_ids")
    op.drop_column("investment_memos", "claim_ids")
    op.drop_index("ix_claims_opportunity_id", table_name="claims")
    op.drop_column("claims", "opportunity_id")
    op.drop_index("ix_observations_opportunity_id", table_name="observations")
    op.drop_column("observations", "opportunity_id")
