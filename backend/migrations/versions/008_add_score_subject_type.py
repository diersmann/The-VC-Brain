"""add subject_type column to score_snapshots

Replaces the fragile rubric_version LIKE heuristic with an explicit
polymorphic discriminator column.

Revision ID: 008
Revises: e093be299381
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: str | None = "e093be299381"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "score_snapshots",
        sa.Column("subject_type", sa.String(32), nullable=True),
    )
    # All existing rows are person-scoped.
    op.execute("UPDATE score_snapshots SET subject_type = 'person'")
    op.alter_column("score_snapshots", "subject_type", nullable=False)
    op.create_index(
        "ix_score_snapshots_subject_type",
        "score_snapshots",
        ["subject_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_score_snapshots_subject_type", table_name="score_snapshots")
    op.drop_column("score_snapshots", "subject_type")
