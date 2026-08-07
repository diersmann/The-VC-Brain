"""Small durable lifecycle helpers for asynchronous jobs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobRun


async def create_job(session: AsyncSession, job_type: str) -> JobRun:
    """Create and flush a queued job record before dispatch."""
    job = JobRun(job_type=job_type, status="queued", phase="queued")
    session.add(job)
    await session.flush()
    return job


async def update_job(
    session: AsyncSession,
    job_id: str | uuid.UUID,
    *,
    status: str,
    phase: str,
    attempt: int | None = None,
    progress: float | None = None,
    last_error: str | None = None,
    clear_error: bool = False,
    result: dict[str, Any] | None = None,
) -> JobRun | None:
    """Apply a bounded, durable status update to a known job."""
    try:
        parsed_id = job_id if isinstance(job_id, uuid.UUID) else uuid.UUID(job_id)
    except (ValueError, AttributeError):
        return None
    job = await session.get(JobRun, parsed_id)
    if job is None:
        return None
    now = datetime.now(UTC)
    job.status = status
    job.phase = phase
    if attempt is not None:
        job.attempt = max(0, attempt)
    if progress is not None:
        job.progress = max(0.0, min(1.0, progress))
    if clear_error:
        job.last_error = None
    elif last_error is not None:
        job.last_error = last_error
    if result is not None:
        job.result = result
    if status == "running" and job.started_at is None:
        job.started_at = now
    if status in {"succeeded", "failed", "cancelled"}:
        job.finished_at = now
        if status == "succeeded":
            job.progress = 1.0
    return job


async def start_job(
    session: AsyncSession,
    job_id: str | uuid.UUID,
    *,
    phase: str,
) -> JobRun | None:
    """Mark a queued job running and advance its durable retry attempt."""
    try:
        parsed_id = job_id if isinstance(job_id, uuid.UUID) else uuid.UUID(job_id)
    except (ValueError, AttributeError):
        return None
    job = await session.get(JobRun, parsed_id)
    if job is None:
        return None
    if job.status in {"succeeded", "cancelled"}:
        # Duplicate delivery after a terminal result must be a no-op. Failed
        # jobs remain retryable and are intentionally reopened below.
        return job
    return await update_job(
        session,
        job.id,
        status="running",
        phase=phase,
        attempt=max(1, (job.attempt or 0) + 1),
        clear_error=True,
    )
