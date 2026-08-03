"""add deterministic provenance to score snapshots

Revision ID: 016
Revises: 015
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "016"
down_revision: str | None = "015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "score_snapshots",
        sa.Column("input_fingerprint", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "score_snapshots",
        sa.Column("provenance", postgresql.JSONB, nullable=True),
    )
    op.create_index(
        "ix_score_snapshots_input_fingerprint",
        "score_snapshots",
        ["input_fingerprint"],
    )


def downgrade() -> None:
    op.drop_index("ix_score_snapshots_input_fingerprint", table_name="score_snapshots")
    op.drop_column("score_snapshots", "provenance")
    op.drop_column("score_snapshots", "input_fingerprint")
