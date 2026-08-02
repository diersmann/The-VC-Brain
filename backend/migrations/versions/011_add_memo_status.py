"""add explicit investment memo generation status

Revision ID: 011
Revises: 010
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing rows have no reliable generation outcome; keep them visible but
    # non-ready until a validated run is generated again.
    op.add_column(
        "investment_memos",
        sa.Column("status", sa.String(16), nullable=False, server_default="degraded"),
    )
    op.create_index("ix_investment_memos_status", "investment_memos", ["status"])


def downgrade() -> None:
    op.drop_index("ix_investment_memos_status", table_name="investment_memos")
    op.drop_column("investment_memos", "status")
