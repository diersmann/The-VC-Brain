"""add privacy-purpose and external AI policy metadata

Revision ID: 022
Revises: 021
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "022"
down_revision: str | None = "021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "persons", sa.Column("privacy_legal_basis", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "persons", sa.Column("privacy_notice_version", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "persons",
        sa.Column(
            "privacy_purposes",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "persons",
        sa.Column("privacy_provider_policy_version", sa.String(length=64), nullable=True),
    )
    op.add_column("persons", sa.Column("privacy_retention_days", sa.Integer(), nullable=True))
    op.add_column("persons", sa.Column("privacy_residency", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("persons", "privacy_residency")
    op.drop_column("persons", "privacy_retention_days")
    op.drop_column("persons", "privacy_provider_policy_version")
    op.drop_column("persons", "privacy_purposes")
    op.drop_column("persons", "privacy_notice_version")
    op.drop_column("persons", "privacy_legal_basis")
