"""add lifecycle stages

Revision ID: 007
Revises: 006
Create Date: 2026-07-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Backfill: existing outbound opportunities at "screening" move to
    # "discovered" so they re-enter the pipeline at the right stage.
    op.execute(
        "UPDATE opportunities "
        "SET lifecycle_state = 'discovered' "
        "WHERE source_kind = 'outbound' AND lifecycle_state = 'screening'"
    )

    # Add CHECK constraint (includes legacy states so existing inbound data
    # is not rejected).
    op.create_check_constraint(
        "chk_opportunities_lifecycle_state",
        "opportunities",
        "lifecycle_state IN ("
        "'discovered','interesting','investigating','contacted',"
        "'received','memo_ready','hold','approved','closed',"
        "'screening','triage','diligence'"
        ")",
    )

    # Fast stage filtering.
    op.create_index(
        "ix_opportunities_lifecycle_state",
        "opportunities",
        ["lifecycle_state"],
    )


def downgrade() -> None:
    op.drop_index("ix_opportunities_lifecycle_state", table_name="opportunities")
    op.drop_constraint(
        "chk_opportunities_lifecycle_state", "opportunities", type_="check"
    )
    op.execute(
        "UPDATE opportunities "
        "SET lifecycle_state = 'screening' "
        "WHERE source_kind = 'outbound' AND lifecycle_state = 'discovered'"
    )
