"""add idempotent inbound submissions and durable outbox

Revision ID: 009
Revises: 008
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column[object], sa.Column[object]]:
    return (
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def upgrade() -> None:
    created_at, updated_at = _timestamps()
    op.create_table(
        "inbound_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("persons.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_snapshots.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="accepted"),
        created_at,
        updated_at,
        sa.UniqueConstraint("idempotency_key", name="uq_inbound_submissions_idempotency_key"),
    )
    op.create_index(
        "ix_inbound_submissions_idempotency_key", "inbound_submissions", ["idempotency_key"]
    )

    created_at, updated_at = _timestamps()
    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dedupe_key", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        created_at,
        updated_at,
        sa.UniqueConstraint("dedupe_key", name="uq_outbox_events_dedupe_key"),
    )
    op.create_index("ix_outbox_events_dedupe_key", "outbox_events", ["dedupe_key"])
    op.create_index("ix_outbox_events_ready", "outbox_events", ["status", "available_at"])


def downgrade() -> None:
    op.drop_index("ix_outbox_events_ready", table_name="outbox_events")
    op.drop_index("ix_outbox_events_dedupe_key", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index("ix_inbound_submissions_idempotency_key", table_name="inbound_submissions")
    op.drop_table("inbound_submissions")
