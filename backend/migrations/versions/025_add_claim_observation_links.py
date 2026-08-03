"""add typed claim-to-observation evidence links

Revision ID: 025
Revises: 024
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "025"
down_revision: str | None = "024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "claim_observations",
        sa.Column(
            "claim_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("claims.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "observation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("observations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("claim_id", "observation_id"),
    )
    op.create_index(
        "ix_claim_observations_observation_id", "claim_observations", ["observation_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_claim_observations_observation_id", table_name="claim_observations")
    op.drop_table("claim_observations")
