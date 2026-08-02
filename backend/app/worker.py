"""Arq background worker for the data collector.

Registers jobs and cron schedules.  The worker is started by the
``compose.yaml`` ``worker`` service (or manually via ``arq app.worker.WorkerSettings``).
"""

from __future__ import annotations

from typing import Any

import structlog
from arq.connections import RedisSettings
from arq.cron import cron
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contact_job import contact_outbound_job
from app.agents.inbound_job import process_inbound_pitch_job
from app.agents.lifecycle_job import advance_pipeline_job
from app.agents.memo_job import generate_memo_job
from app.agents.outbox_job import dispatch_outbox_job
from app.agents.scoring_job import score_candidate_job
from app.collectors.jobs import (
    auto_discovery_job,
    collect_job,
    discover_job,
    dispatcher_job,
    fetch_candidate_avatar_job,
    recompute_signals_job,
    research_candidate_job,
    resolve_identities_job,
)
from app.collectors.queue import initialize_agent_budget, reset_tavily_budget
from app.config import get_settings
from app.db.session import _get_session_factory, get_engine
from app.processing.pipeline_job import process_candidate_job

logger = structlog.get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    """Arq startup hook — create DB session factory and ensure MinIO bucket."""
    settings = get_settings()
    ctx["settings"] = settings
    ctx["session_factory"] = _get_session_factory()

    # Reset Tavily budget on worker start (in production, this should be
    # a monthly cron, but for MVP it's fine to reset on deploy).
    await reset_tavily_budget(ctx["redis"], settings.tavily_monthly_budget)
    await initialize_agent_budget(ctx["redis"], settings.agent_monthly_budget)

    logger.info("worker_started", environment=settings.environment)


async def shutdown(ctx: dict[str, Any]) -> None:
    """Arq shutdown hook — dispose DB engine."""
    engine = get_engine()
    await engine.dispose()
    logger.info("worker_shutdown")


async def get_session(ctx: dict[str, Any]) -> AsyncSession:
    """Return a DB session from the factory stored in ctx."""
    factory = ctx.get("session_factory")
    if factory is None:
        msg = "session_factory not initialized — did startup() run?"
        raise RuntimeError(msg)
    session: AsyncSession = factory()
    return session


class WorkerSettings:
    """Arq worker configuration.

    NOTE: Arq's ``get_kwargs()`` reads from ``__dict__`` (class-level
    attributes only).  Properties and ``__init__``-set attributes are
    NOT visible to Arq.  Everything must be a plain class attribute.
    """

    functions: list[Any] = [  # noqa: RUF012
        discover_job,
        collect_job,
        dispatcher_job,
        fetch_candidate_avatar_job,
        recompute_signals_job,
        research_candidate_job,
        resolve_identities_job,
        score_candidate_job,
        generate_memo_job,
        process_candidate_job,
        advance_pipeline_job,
        contact_outbound_job,
        auto_discovery_job,
        process_inbound_pitch_job,
        dispatch_outbox_job,
    ]

    cron_jobs = [  # noqa: RUF012
        cron(dispatch_outbox_job, unique=False),
        # dispatcher_job: every minute
        cron(dispatcher_job, unique=False),
        # recompute_signals_job: every hour at minute 5
        cron(recompute_signals_job, minute={5}, unique=False),
        # auto_discovery_job: every hour at minute 15
        cron(auto_discovery_job, minute={15}, unique=False),
        # resolve_identities_job: every hour at minute 25
        cron(resolve_identities_job, minute={25}, unique=False),
        # advance_pipeline_job: every 2 minutes (unique to prevent overlap)
        cron(
            advance_pipeline_job,
            minute={
                0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30,
                32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58,
            },
            unique=True,
        ),
    ]

    on_startup = startup
    on_shutdown = shutdown
    keep_result = 3600  # keep job results for 1 hour
    max_tries = 3
    job_timeout = 300  # 5 minutes default
    max_burst_jobs = 10

    # Redis settings — computed at class definition time from env vars.
    # Arq reads this from __dict__, so it must be a class attribute.
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
