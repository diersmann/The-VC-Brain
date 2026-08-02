"""add idempotency keys to decision events

Revision ID: 013
Revises: 012
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "decision_events",
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
    )
    op.create_unique_constraint(
        "uq_decision_events_idempotency_key",
        "decision_events",
        ["idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_decision_events_idempotency_key",
        "decision_events",
        type_="unique",
    )
    op.drop_column("decision_events", "idempotency_key")
