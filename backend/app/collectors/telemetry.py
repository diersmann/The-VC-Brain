"""Durable, provider-neutral connector runtime telemetry."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ConnectorTelemetry


async def record_connector_success(
    session: AsyncSession,
    source_type: str,
    *,
    occurred_at: datetime | None = None,
) -> None:
    """Persist the newest successful connector-operation timestamp.

    This watermark is intentionally written in the same transaction as the
    job's source/observation persistence.  A provider response that later
    fails validation or cannot be committed therefore cannot make health look
    successful.  PostgreSQL's upsert keeps concurrent workers safe and the
    ``greatest`` guard prevents an older retry from moving the watermark
    backwards.
    """

    if not isinstance(source_type, str) or not source_type.strip():
        raise ValueError("source_type must be a non-empty string")
    timestamp = occurred_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    else:
        timestamp = timestamp.astimezone(UTC)

    statement = insert(ConnectorTelemetry).values(
        source_type=source_type,
        last_success_at=timestamp,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[ConnectorTelemetry.source_type],
        set_={
            "last_success_at": func.greatest(
                ConnectorTelemetry.last_success_at,
                statement.excluded.last_success_at,
            ),
            "updated_at": func.now(),
        },
    )
    await session.execute(statement)
