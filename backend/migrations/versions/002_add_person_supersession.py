"""add person supersession and person_matches

Revision ID: 002
Revises: 001
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Persons: add supersession columns
    # -----------------------------------------------------------------------
    op.add_column(
        "persons",
        sa.Column(
            "superseded_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("persons.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    op.add_column(
        "persons",
        sa.Column("canonical", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
    )
    op.add_column(
        "persons",
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Backfill: all existing persons are canonical
    op.execute("UPDATE persons SET canonical = TRUE WHERE canonical IS NULL")

    # -----------------------------------------------------------------------
    # Person Matches (identity resolution review queue)
    # -----------------------------------------------------------------------
    op.create_table(
        "person_matches",
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
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("reasons", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("resolved_by", sa.String(128), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("person_matches")
    op.drop_column("persons", "merged_at")
    op.drop_column("persons", "canonical")
    op.drop_column("persons", "superseded_by_id")
