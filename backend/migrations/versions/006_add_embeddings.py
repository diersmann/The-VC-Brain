"""add observation embeddings

Revision ID: 006
Revises: 005
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "observations",
        sa.Column("embedding", Vector(1536), nullable=True),
    )
    # IVFFLAT index for fast cosine similarity search
    op.execute(
        "CREATE INDEX ix_observations_embedding ON observations "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_observations_embedding")
    op.drop_column("observations", "embedding")