"""Processing pipeline job — reconcile + embed + dedup."""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.collectors.jobs import _session_ctx
from app.processing.dedup import deduplicate_claims
from app.processing.embeddings import embed_observations
from app.processing.reconcile import reconcile_observations

logger = structlog.get_logger(__name__)


async def process_candidate_job(ctx: dict[str, Any], person_id: str) -> dict[str, Any]:
    """Run the full processing pipeline for a candidate.

    Steps:
        1. Reconcile observations into Claims (resolve contradictions).
        2. Generate embeddings for all observations.
        3. Deduplicate claims using embedding similarity.

    Returns a summary dict.
    """
    from app.config import get_settings

    settings = ctx.get("settings") or get_settings()
    logger.info("process_candidate_job_started", person_id=person_id)

    async with _session_ctx(ctx) as session:
        pid = uuid.UUID(person_id)

        # 1. Reconcile
        claims_created = await reconcile_observations(session, pid)

        # 2. Embed
        embeddings_generated = await embed_observations(
            session,
            pid,
            api_key=settings.llm_api_key,
            model=settings.embedding_model,
            concurrency=settings.embedding_concurrency,
        )

        # 3. Dedup
        claims_deduped = await deduplicate_claims(session, pid)

        await session.commit()

    logger.info(
        "process_candidate_job_completed",
        person_id=person_id,
        claims_created=claims_created,
        embeddings_generated=embeddings_generated,
        claims_deduped=claims_deduped,
    )

    return {
        "person_id": person_id,
        "claims_created": claims_created,
        "embeddings_generated": embeddings_generated,
        "claims_deduped": claims_deduped,
    }