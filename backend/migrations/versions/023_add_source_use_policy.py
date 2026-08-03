"""persist explicit source-use policy decisions

Revision ID: 023
Revises: 022
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "023"
down_revision: str | None = "022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_UNKNOWN_POLICY = (
    "'{\"version\":\"source-use-v1\",\"status\":\"unknown\","
    "\"model_use\":\"denied\"}'::jsonb"
)


def upgrade() -> None:
    op.add_column(
        "source_snapshots",
        sa.Column(
            "source_use_policy",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text(_UNKNOWN_POLICY),
        ),
    )


def downgrade() -> None:
    op.drop_column("source_snapshots", "source_use_policy")
