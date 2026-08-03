"""add append-only opportunity channel touches

Revision ID: 028
Revises: 027
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "028"
down_revision: str | None = "027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "opportunity_channel_touches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("touch_type", sa.String(length=64), nullable=False),
        sa.Column("source_query", sa.Text(), nullable=True),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opportunity_channel_touches_opportunity_id",
        "opportunity_channel_touches",
        ["opportunity_id"],
    )
    op.create_index(
        "ix_opportunity_channel_touches_channel",
        "opportunity_channel_touches",
        ["channel"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunity_channel_touches_channel", table_name="opportunity_channel_touches"
    )
    op.drop_index(
        "ix_opportunity_channel_touches_opportunity_id", table_name="opportunity_channel_touches"
    )
    op.drop_table("opportunity_channel_touches")
