"""Processing pipeline job — reconcile + embed + dedup."""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.collectors.base import classify_connector_failure
from app.collectors.jobs import _session_ctx
from app.db.models import Person
from app.job_ledger import create_job, start_job, update_job
from app.privacy import external_ai_use_decision
from app.processing.dedup import deduplicate_claims
from app.processing.embeddings import embed_observations
from app.processing.reconcile import reconcile_observations

logger = structlog.get_logger(__name__)


async def process_candidate_job(
    ctx: dict[str, Any], person_id: str, job_id: str | None = None
) -> dict[str, Any]:
    """Run the full processing pipeline for a candidate.

    Steps:
        1. Reconcile observations into Claims (resolve contradictions).
        2. Generate embeddings for all observations.
        3. Deduplicate claims using embedding similarity.

    Returns a summary dict.
    """
    logger.info("process_candidate_job_started", person_id=person_id)

    async with _session_ctx(ctx) as session:
        ledger_job_id = job_id
        job_attempt = 1
        result: dict[str, Any]
        try:
            if ledger_job_id is None:
                created_job = await create_job(session, "process_candidate")
                ledger_job_id = str(created_job.id)
            started_job = await start_job(session, ledger_job_id, phase="processing")
            if started_job is not None:
                job_attempt = started_job.attempt
                if started_job.status in {"succeeded", "cancelled"}:
                    await session.commit()
                    return dict(started_job.result or {"status": started_job.status})
            await session.commit()
            logger.info(
                "process_candidate_job_running",
                person_id=person_id,
                job_id=ledger_job_id,
                attempt=job_attempt,
            )

            from app.config import get_settings

            settings = ctx.get("settings") or get_settings()
            pid = uuid.UUID(person_id)
            person = await session.get(Person, pid)
            if person is None:
                result = {"error": "person_not_found", "person_id": person_id}
                if ledger_job_id:
                    await update_job(
                        session,
                        ledger_job_id,
                        status="failed",
                        phase="processing",
                        attempt=job_attempt,
                        last_error="person_not_found",
                        result={
                            "status": "failed",
                            "error": "person_not_found",
                            "person_id": person_id,
                            "failure_kind": "permanent",
                            "retryable": False,
                        },
                    )
                await session.commit()
                return result

            # 1. Reconcile
            claims_created = await reconcile_observations(session, pid)

            # 2. Embed
            embedding_api_key = settings.llm_api_key
            if embedding_api_key and not external_ai_use_decision(person, "embeddings").allowed:
                embedding_api_key = ""
            embeddings_generated = await embed_observations(
                session,
                pid,
                api_key=embedding_api_key,
                model=settings.embedding_model,
                concurrency=settings.embedding_concurrency,
            )

            # 3. Dedup
            claims_deduped = await deduplicate_claims(session, pid)

            result = {
                "person_id": person_id,
                "claims_created": claims_created,
                "embeddings_generated": embeddings_generated,
                "claims_deduped": claims_deduped,
            }
            if ledger_job_id:
                await update_job(
                    session,
                    ledger_job_id,
                    status="succeeded",
                    phase="complete",
                    attempt=job_attempt,
                    clear_error=True,
                    result=result,
                )
            await session.commit()
        except Exception as exc:
            failure_kind, retryable = classify_connector_failure(exc)
            logger.error(
                "process_candidate_job_failed",
                person_id=person_id,
                failure_kind=failure_kind,
                retryable=retryable,
                error_type=type(exc).__name__,
            )
            if ledger_job_id:
                try:
                    await session.rollback()
                    await update_job(
                        session,
                        ledger_job_id,
                        status="failed",
                        phase="processing",
                        attempt=job_attempt,
                        last_error=str(exc),
                        result={
                            "status": "failed",
                            "error": str(exc),
                            "person_id": person_id,
                            "failure_kind": failure_kind,
                            "retryable": retryable,
                        },
                    )
                    await session.commit()
                except Exception as ledger_exc:
                    logger.error(
                        "process_candidate_job_ledger_update_failed",
                        job_id=ledger_job_id,
                        error_type=type(ledger_exc).__name__,
                    )
            raise

    logger.info(
        "process_candidate_job_completed",
        person_id=person_id,
        claims_created=claims_created,
        embeddings_generated=embeddings_generated,
        claims_deduped=claims_deduped,
    )

    return result
