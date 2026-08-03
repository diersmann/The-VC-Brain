"""Arq job that dispatches committed outbox events to Redis."""

from __future__ import annotations

from typing import Any

from app.collectors.jobs import _session_ctx
from app.outbox import dispatch_pending_outbox


async def dispatch_outbox_job(ctx: dict[str, Any]) -> dict[str, int]:
    async with _session_ctx(ctx) as session:
        return await dispatch_pending_outbox(session, ctx["redis"])
