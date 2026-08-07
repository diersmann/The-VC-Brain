"""add non-destructive database fingerprints for collector persistence

Revision ID: 031
Revises: 030
Create Date: 2026-08-07

Existing duplicate rows are deliberately retained.  The backfill assigns a
fingerprint only to the deterministic first row in each natural-key group;
remaining legacy duplicates stay NULL so this migration never deletes or
rewrites evidence.  New rows carry a fingerprint and are protected by the
partial unique indexes below.  A later, policy-approved cleanup can reconcile
the retained legacy duplicates before making the columns non-null.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "031"
down_revision: str | None = "030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None



def _length_prefixed_sql(expression: str) -> str:
    """Build the SQL equivalent of the application UTF-8 key encoding."""
    value = f"coalesce({expression}, '')"
    return f"(octet_length(convert_to({value}, 'UTF8'))::text || ':' || {value})"


def upgrade() -> None:
    op.add_column(
        "source_snapshots",
        sa.Column("persistence_fingerprint", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "observations",
        sa.Column("persistence_fingerprint", sa.String(length=32), nullable=True),
    )

    # Keep every row, but choose one deterministic representative per natural
    # key for the unique-index window. Rows left NULL are explicit legacy
    # duplicates and remain available for later review/reconciliation.
    snapshot_key = " || ".join(
        _length_prefixed_sql(expression)
        for expression in ("uri", "source_type", "content_hash")
    )
    observation_key = " || ".join(
        _length_prefixed_sql(expression)
        for expression in (
            "snapshot_id::text",
            "subject_id::text",
            "opportunity_id::text",
            "predicate",
            "object_value",
            "extractor_version",
        )
    )
    op.execute(
        sa.text(
            f"""
            WITH ranked AS (
                SELECT
                    id,
                    md5({snapshot_key}) AS fingerprint,
                    row_number() OVER (
                        PARTITION BY uri, source_type, content_hash
                        ORDER BY created_at ASC, id ASC
                    ) AS row_number
                FROM source_snapshots
            )
            UPDATE source_snapshots AS target
            SET persistence_fingerprint = ranked.fingerprint
            FROM ranked
            WHERE target.id = ranked.id
              AND ranked.row_number = 1
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            WITH ranked AS (
                SELECT
                    id,
                    md5({observation_key}) AS fingerprint,
                    row_number() OVER (
                        PARTITION BY snapshot_id, subject_id, opportunity_id,
                                     predicate, object_value, extractor_version
                        ORDER BY created_at ASC, id ASC
                    ) AS row_number
                FROM observations
            )
            UPDATE observations AS target
            SET persistence_fingerprint = ranked.fingerprint
            FROM ranked
            WHERE target.id = ranked.id
              AND ranked.row_number = 1
            """
        )
    )

    op.create_index(
        "uq_source_snapshots_persistence_fingerprint",
        "source_snapshots",
        ["persistence_fingerprint"],
        unique=True,
        postgresql_where=sa.text("persistence_fingerprint IS NOT NULL"),
    )
    op.create_index(
        "uq_observations_persistence_fingerprint",
        "observations",
        ["persistence_fingerprint"],
        unique=True,
        postgresql_where=sa.text("persistence_fingerprint IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_observations_persistence_fingerprint", table_name="observations"
    )
    op.drop_index(
        "uq_source_snapshots_persistence_fingerprint", table_name="source_snapshots"
    )
    op.drop_column("observations", "persistence_fingerprint")
    op.drop_column("source_snapshots", "persistence_fingerprint")
