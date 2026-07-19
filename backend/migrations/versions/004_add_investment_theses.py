"""add versioned investment theses

Revision ID: 004
Revises: 003
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "investment_theses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stages", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("sectors", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("excluded_sectors", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("regions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("check_size_min_k_eur", sa.Float(), nullable=True),
        sa.Column("check_size_max_k_eur", sa.Float(), nullable=True),
        sa.Column("ownership_target_pct", sa.Float(), nullable=True),
        sa.Column(
            "risk_appetite", sa.String(32), nullable=False, server_default="balanced"
        ),
        sa.Column("scoring_weights", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_investment_theses_version", "investment_theses", ["version"])
    op.create_index("ix_investment_theses_is_active", "investment_theses", ["is_active"])
    op.create_index(
        "uq_investment_theses_one_active",
        "investment_theses",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    op.drop_index("uq_investment_theses_one_active", table_name="investment_theses")
    op.drop_index("ix_investment_theses_is_active", table_name="investment_theses")
    op.drop_index("ix_investment_theses_version", table_name="investment_theses")
    op.drop_table("investment_theses")
