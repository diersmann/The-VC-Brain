"""add append-only candidate feedback

Revision ID: 018
Revises: 017
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "018"
down_revision: str | None = "017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidate_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("undone_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_candidate_feedback_person_id", "candidate_feedback", ["person_id"])
    op.create_index("ix_candidate_feedback_action", "candidate_feedback", ["action"])


def downgrade() -> None:
    op.drop_index("ix_candidate_feedback_action", table_name="candidate_feedback")
    op.drop_index("ix_candidate_feedback_person_id", table_name="candidate_feedback")
    op.drop_table("candidate_feedback")
