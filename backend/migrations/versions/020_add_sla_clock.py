"""add persisted inbound decision SLA clock

Revision ID: 020
Revises: 019
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "020"
down_revision: str | None = "019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("received_at", sa.DateTime(timezone=True)))
    op.add_column("opportunities", sa.Column("decision_due_at", sa.DateTime(timezone=True)))
    op.add_column(
        "opportunities",
        sa.Column(
            "stage_deadlines",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column("opportunities", sa.Column("sla_owner", sa.String(length=128)))
    op.add_column("opportunities", sa.Column("sla_pause_reason", sa.Text()))
    op.add_column(
        "opportunities",
        sa.Column("sla_attainment", sa.String(length=16), nullable=False, server_default="pending"),
    )
    op.add_column("opportunities", sa.Column("sla_decided_at", sa.DateTime(timezone=True)))
    op.create_check_constraint(
        "ck_opportunities_sla_attainment",
        "opportunities",
        "sla_attainment IN ('pending','met','breached')",
    )

    # Existing inbound records are known to have entered at creation time.
    # Backfill the clock without fabricating an owner or decision outcome.
    op.execute(
        """
        UPDATE opportunities
        SET received_at = created_at,
            decision_due_at = created_at + interval '24 hours',
            stage_deadlines = jsonb_build_object(
                'triage', (created_at + interval '30 minutes')::text,
                'screening', (created_at + interval '3 hours 30 minutes')::text,
                'diligence', (created_at + interval '17 hours 30 minutes')::text,
                'memo', (created_at + interval '21 hours 30 minutes')::text,
                'human_decision', (created_at + interval '24 hours')::text
            )
        WHERE source_kind = 'inbound' AND received_at IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_opportunities_sla_attainment", "opportunities", type_="check"
    )
    op.drop_column("opportunities", "sla_decided_at")
    op.drop_column("opportunities", "sla_attainment")
    op.drop_column("opportunities", "sla_pause_reason")
    op.drop_column("opportunities", "sla_owner")
    op.drop_column("opportunities", "stage_deadlines")
    op.drop_column("opportunities", "decision_due_at")
    op.drop_column("opportunities", "received_at")
