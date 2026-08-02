"""add source coordinates to observations

Revision ID: 015
Revises: 014
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "observations",
        sa.Column("source_locator", postgresql.JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("observations", "source_locator")
