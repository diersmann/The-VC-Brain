"""add persisted outreach delivery state

Revision ID: 010
Revises: 009
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outreach_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("persons.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("recipient_email", sa.String(320), nullable=True),
        sa.Column("subject", sa.String(240), nullable=False, server_default=""),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        sa.Column("generation_mode", sa.String(32), nullable=False, server_default="template"),
        sa.Column("status", sa.String(24), nullable=False, server_default="drafted"),
        sa.Column("approved_by", sa.String(128), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("failure_reason", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_outreach_messages_status", "outreach_messages", ["status"])
    op.create_index(
        "ix_outreach_messages_person_created",
        "outreach_messages",
        ["person_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_outreach_messages_person_created", table_name="outreach_messages")
    op.drop_index("ix_outreach_messages_status", table_name="outreach_messages")
    op.drop_table("outreach_messages")
