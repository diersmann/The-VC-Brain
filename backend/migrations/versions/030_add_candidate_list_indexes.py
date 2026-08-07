"""add indexes used by candidate list cursor pagination

Revision ID: 030
Revises: 029
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "030"
down_revision: str | None = "029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_persons_candidate_cursor",
        "persons",
        ["created_at", "id"],
        postgresql_using="btree",
    )
    op.create_index(
        "ix_observations_subject_observed_at",
        "observations",
        ["subject_id", "observed_at"],
        postgresql_using="btree",
    )
    op.create_index(
        "ix_opportunity_founders_person_opportunity",
        "opportunity_founders",
        ["person_id", "opportunity_id"],
        postgresql_using="btree",
    )
    op.create_index(
        "ix_opportunities_candidate_order",
        "opportunities",
        ["created_at", "id", "source_kind", "lifecycle_state"],
        postgresql_using="btree",
    )


def downgrade() -> None:
    op.drop_index("ix_observations_subject_observed_at", table_name="observations")
    op.drop_index(
        "ix_opportunities_candidate_order", table_name="opportunities"
    )
    op.drop_index(
        "ix_opportunity_founders_person_opportunity", table_name="opportunity_founders"
    )
    op.drop_index("ix_persons_candidate_cursor", table_name="persons")
