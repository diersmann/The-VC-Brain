"""add versioned claim trust artifacts

Revision ID: 014
Revises: 013
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("claims", sa.Column("trust_version", sa.String(length=64), nullable=True))
    op.add_column("claims", sa.Column("trust_score", sa.Float(), nullable=True))
    op.add_column("claims", sa.Column("trust_interval", postgresql.JSONB, nullable=True))
    op.add_column("claims", sa.Column("trust_components", postgresql.JSONB, nullable=True))
    op.add_column("claims", sa.Column("trust_explanation", sa.Text(), nullable=True))
    op.execute(
        "UPDATE claims SET trust_version = 'legacy-unknown', "
        "trust_score = confidence, "
        "trust_interval = jsonb_build_object('low', 0.0, 'high', 1.0), "
        "trust_components = jsonb_build_object('legacy', true), "
        "trust_explanation = 'Legacy claim without versioned trust inputs.'"
    )


def downgrade() -> None:
    op.drop_column("claims", "trust_explanation")
    op.drop_column("claims", "trust_components")
    op.drop_column("claims", "trust_interval")
    op.drop_column("claims", "trust_score")
    op.drop_column("claims", "trust_version")
