"""store cached candidate avatars

Revision ID: 003
Revises: 002
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("persons", sa.Column("avatar_data", sa.LargeBinary(), nullable=True))
    op.add_column("persons", sa.Column("avatar_mime_type", sa.String(64), nullable=True))
    op.add_column("persons", sa.Column("avatar_sha256", sa.String(64), nullable=True))
    op.add_column("persons", sa.Column("avatar_source_type", sa.String(32), nullable=True))
    op.add_column("persons", sa.Column("avatar_source_url", sa.Text(), nullable=True))
    op.add_column("persons", sa.Column("avatar_image_url", sa.Text(), nullable=True))
    op.add_column(
        "persons",
        sa.Column("avatar_fetched_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("persons", "avatar_fetched_at")
    op.drop_column("persons", "avatar_image_url")
    op.drop_column("persons", "avatar_source_url")
    op.drop_column("persons", "avatar_source_type")
    op.drop_column("persons", "avatar_sha256")
    op.drop_column("persons", "avatar_mime_type")
    op.drop_column("persons", "avatar_data")
