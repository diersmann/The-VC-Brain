"""add first-class organization linkage and temporal founder roles

Revision ID: 024
Revises: 023
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "024"
down_revision: str | None = "023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_opportunities_organization_id", "opportunities", ["organization_id"]
    )
    op.add_column(
        "opportunity_founders",
        sa.Column("role", sa.String(length=64), nullable=False, server_default="founder"),
    )
    op.add_column(
        "opportunity_founders",
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "opportunity_founders", sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("opportunity_founders", "valid_to")
    op.drop_column("opportunity_founders", "valid_from")
    op.drop_column("opportunity_founders", "role")
    op.drop_index("ix_opportunities_organization_id", table_name="opportunities")
    op.drop_column("opportunities", "organization_id")
