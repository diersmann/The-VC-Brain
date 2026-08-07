"""Arq job for processing inbound pitch submissions."""

from __future__ import annotations

import asyncio
import inspect
import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from app.collectors.base import classify_connector_failure
from app.collectors.jobs import _session_ctx
from app.collectors.persistence import observation_persistence_fingerprint
from app.config import get_settings
from app.db.models import JobRun, Observation, SourceSnapshot
from app.job_ledger import create_job, start_job, update_job
from app.processing.pipeline_job import process_candidate_job
from app.storage import get_snapshot
from app.uploads import UploadRejected, extract_pdf_pages

logger = structlog.get_logger(__name__)


def _failure_result(
    error: str,
    *,
    person_id: str,
    snapshot_id: str,
    opportunity_id: str,
    job_id: str | None,
    failure_kind: str,
    retryable: bool,
) -> dict[str, Any]:
    """Build a safe, provider-neutral terminal result.

    Uploaded documents and storage/DB exception text can contain founder data
    or implementation details.  The durable result therefore keeps only a
    stable error code and the shared retry classification; the worker log
    records the exception type separately.
    """
    return {
        "status": "failed",
        "error": error,
        "person_id": person_id,
        "snapshot_id": snapshot_id,
        "opportunity_id": opportunity_id,
        "job_id": job_id,
        "failure_kind": failure_kind,
        "retryable": retryable,
    }


def _observation_key(observation: Observation) -> tuple[str, str, str, str]:
    """Return a retry key that preserves repeated text on different pages."""
    locator = json.dumps(
        observation.source_locator or {},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return (
        observation.predicate,
        observation.object_value,
        observation.extractor_version,
        locator,
    )

async def process_inbound_pitch_job(
    ctx: dict[str, Any],
    person_id: str,
    snapshot_id: str,
    opportunity_id: str,
    company_name: str,
    founder_evidence: dict[str, str] | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Process an uploaded pitch deck.
    
    Extracts text and runs the generic processing pipeline. The lifecycle
    worker schedules Founder Score, opportunity research, and memo generation
    only after their required upstream outputs exist.
    """
    logger.info("process_inbound_pitch_started", person_id=person_id, snapshot_id=snapshot_id)

    async with _session_ctx(ctx) as session:
        ledger_job_id = job_id
        job_attempt = 1

        async def terminalize(
            result: dict[str, Any],
            *,
            rollback: bool = False,
            phase: str = "parsing",
        ) -> None:
            """Persist a failed terminal state without leaking exception text."""
            if ledger_job_id is None:
                return
            try:
                if rollback:
                    await session.rollback()
                await update_job(
                    session,
                    ledger_job_id,
                    status="failed",
                    phase=phase,
                    attempt=job_attempt,
                    last_error=str(result["error"]),
                    result=result,
                )
                await session.commit()
            except Exception as ledger_exc:  # pragma: no cover - DB outage path
                logger.error(
                    "process_inbound_pitch_ledger_update_failed",
                    job_id=ledger_job_id,
                    error_type=type(ledger_exc).__name__,
                )

        # Create/start and commit the run before touching untrusted PDF bytes.
        # A legacy outbox task may omit the ID; in that case the worker creates
        # an internal run and logs it without exposing the identifier in user
        # data.
        try:
            if ledger_job_id is None:
                # Legacy tasks have no caller-supplied ID. Derive one from the
                # immutable input identity so redelivery reopens the same run
                # instead of inserting duplicate observations/runs.
                derived_job_id = uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"vcbrain:inbound:{person_id}:{snapshot_id}:{opportunity_id}",
                )
                existing_job = await session.get(JobRun, derived_job_id)
                if existing_job is None:
                    await create_job(
                        session,
                        "process_inbound_pitch",
                        job_id=derived_job_id,
                    )
                ledger_job_id = str(derived_job_id)
                logger.info("process_inbound_pitch_job_created", job_id=ledger_job_id)
            started_job = await start_job(session, ledger_job_id, phase="parsing")
            if started_job is not None:
                job_attempt = started_job.attempt
                if started_job.status in {"succeeded", "cancelled"}:
                    await session.commit()
                    return dict(started_job.result or {"status": started_job.status})
            await session.commit()
        except Exception as exc:
            failure_kind, retryable = classify_connector_failure(exc)
            failure = _failure_result(
                "job_start_failed",
                person_id=person_id,
                snapshot_id=snapshot_id,
                opportunity_id=opportunity_id,
                job_id=ledger_job_id,
                failure_kind=failure_kind,
                retryable=retryable,
            )
            await terminalize(failure, rollback=True)
            raise

        try:
            snapshot = await session.get(SourceSnapshot, uuid.UUID(snapshot_id))
        except Exception as exc:
            failure_kind, retryable = classify_connector_failure(exc)
            failure = _failure_result(
                "database_failure",
                person_id=person_id,
                snapshot_id=snapshot_id,
                opportunity_id=opportunity_id,
                job_id=ledger_job_id,
                failure_kind=failure_kind,
                retryable=retryable,
            )
            await terminalize(failure, rollback=True)
            raise

        if snapshot is None:
            failure = _failure_result(
                "snapshot_not_found",
                person_id=person_id,
                snapshot_id=snapshot_id,
                opportunity_id=opportunity_id,
                job_id=ledger_job_id,
                failure_kind="permanent",
                retryable=False,
            )
            logger.warning("snapshot_not_found", snapshot_id=snapshot_id)
            await terminalize(failure)
            return failure

        try:
            content = await get_snapshot(snapshot.storage_path)
        except Exception as exc:
            failure_kind, retryable = classify_connector_failure(exc)
            failure = _failure_result(
                "snapshot_fetch_failed",
                person_id=person_id,
                snapshot_id=snapshot_id,
                opportunity_id=opportunity_id,
                job_id=ledger_job_id,
                failure_kind=failure_kind,
                retryable=retryable,
            )
            await terminalize(failure, rollback=True)
            raise

        try:
            settings = get_settings()
            page_text = await asyncio.to_thread(
                extract_pdf_pages,
                content,
                max_pages=settings.upload_max_pages,
                max_text_chars=settings.upload_max_text_chars,
            )
        except UploadRejected:
            failure = _failure_result(
                "pdf_rejected",
                person_id=person_id,
                snapshot_id=snapshot_id,
                opportunity_id=opportunity_id,
                job_id=ledger_job_id,
                failure_kind="permanent",
                retryable=False,
            )
            logger.warning("pdf_extraction_rejected", snapshot_id=snapshot_id)
            await terminalize(failure)
            return failure
        except Exception as exc:
            failure_kind, retryable = classify_connector_failure(exc)
            failure = _failure_result(
                "pdf_extraction_failed",
                person_id=person_id,
                snapshot_id=snapshot_id,
                opportunity_id=opportunity_id,
                job_id=ledger_job_id,
                failure_kind=failure_kind,
                retryable=retryable,
            )
            logger.error(
                "pdf_extraction_failed",
                snapshot_id=snapshot_id,
                error_type=type(exc).__name__,
                failure_kind=failure_kind,
                retryable=retryable,
            )
            await terminalize(failure, rollback=True)
            raise

        try:
            # Create observations in one transaction with the successful
            # parsing JobRun update. A failed commit rolls back both, so a
            # retry cannot observe a partially persisted deck.
            now = datetime.now(UTC)
            observations_to_add: list[Observation] = []

            # Keep one observation per page so claims can reopen the immutable
            # source at a concrete coordinate instead of a flattened 50k-char blob.
            for text_content, source_locator in page_text:
                observations_to_add.append(
                    Observation(
                        snapshot_id=snapshot.id,
                        subject_id=uuid.UUID(person_id),
                        opportunity_id=uuid.UUID(opportunity_id),
                        predicate="pitch_deck_page_text",
                        object_value=text_content or "[No extractable text on page]",
                        source_locator=source_locator,
                        observed_at=now,
                        extractor_version="inbound-v1",
                        confidence=1.0,
                    )
                )

            observations_to_add.append(
                Observation(
                    snapshot_id=snapshot.id,
                    subject_id=uuid.UUID(person_id),
                    opportunity_id=uuid.UUID(opportunity_id),
                    predicate="company_name",
                    object_value=company_name,
                    observed_at=now,
                    extractor_version="inbound-v1",
                    confidence=1.0,
                )
            )

            evidence_predicates = {
                "work_sample_url": "founder_work_sample_url",
                "work_sample_description": "founder_work_sample_description",
                "learning_velocity": "founder_learning_velocity",
                "reference_context": "founder_reference_context",
                "interview_context": "founder_interview_context",
            }
            for field, value in (founder_evidence or {}).items():
                predicate = evidence_predicates.get(field)
                if predicate is None or not value.strip():
                    continue
                observations_to_add.append(
                    Observation(
                        snapshot_id=snapshot.id,
                        subject_id=uuid.UUID(person_id),
                        opportunity_id=uuid.UUID(opportunity_id),
                        predicate=predicate,
                        object_value=value.strip(),
                        source_locator={"kind": "submission_field", "field": field},
                        observed_at=now,
                        extractor_version="inbound-evidence-v1",
                        confidence=1.0,
                    )
                )

            # The parser can be redelivered after a downstream processing
            # failure. Reuse exact immutable extraction outputs rather than
            # appending duplicate evidence rows (including legacy tasks with
            # no explicit job ID).
            existing_result = await session.execute(
                select(Observation).where(
                    Observation.snapshot_id == snapshot.id,
                    Observation.subject_id == uuid.UUID(person_id),
                    Observation.opportunity_id == uuid.UUID(opportunity_id),
                )
            )
            scalar_result = existing_result.scalars()
            if inspect.isawaitable(scalar_result):
                scalar_result = await scalar_result
            existing_rows = scalar_result.all()
            if inspect.isawaitable(existing_rows):
                existing_rows = await existing_rows
            existing_keys = {
                _observation_key(observation)
                for observation in existing_rows
            } if isinstance(existing_rows, (list, tuple)) else set()
            deduplicated: list[Observation] = []
            for observation in observations_to_add:
                key = _observation_key(observation)
                if key in existing_keys:
                    continue
                observation.persistence_fingerprint = observation_persistence_fingerprint(
                    snapshot_id=observation.snapshot_id,
                    subject_id=observation.subject_id,
                    opportunity_id=observation.opportunity_id,
                    predicate=observation.predicate,
                    object_value=observation.object_value,
                    extractor_version=observation.extractor_version,
                    source_locator=observation.source_locator,
                )
                deduplicated.append(observation)
                existing_keys.add(key)
            observations_to_add = deduplicated

            session.add_all(observations_to_add)
            result = {
                "status": "success",
                "person_id": person_id,
                "snapshot_id": snapshot_id,
                "opportunity_id": opportunity_id,
                "job_id": ledger_job_id,
                "observations_created": len(observations_to_add),
                "next_stage": "inbound_triage",
            }
            # Keep the parsing run non-terminal while the downstream pipeline
            # consumes the newly committed observations.  The pipeline owns
            # its own session, so this commit is the explicit handoff point.
            await update_job(
                session,
                ledger_job_id,
                status="running",
                phase="processing",
                attempt=job_attempt,
                clear_error=True,
                progress=0.8,
            )
            await session.commit()
        except Exception as exc:
            failure_kind, retryable = classify_connector_failure(exc)
            failure = _failure_result(
                "database_failure",
                person_id=person_id,
                snapshot_id=snapshot_id,
                opportunity_id=opportunity_id,
                job_id=ledger_job_id,
                failure_kind=failure_kind,
                retryable=retryable,
            )
            logger.error(
                "process_inbound_pitch_persistence_failed",
                snapshot_id=snapshot_id,
                error_type=type(exc).__name__,
                failure_kind=failure_kind,
                retryable=retryable,
            )
            await terminalize(failure, rollback=True)
            raise

        # Run processing before the lifecycle worker evaluates this
        # opportunity. Keep the parsing JobRun running until this succeeds so
        # a downstream crash remains retryable rather than falsely terminal.
        try:
            processing_result = await process_candidate_job(ctx, person_id)
        except Exception as exc:
            failure_kind, retryable = classify_connector_failure(exc)
            failure = _failure_result(
                "processing_failed",
                person_id=person_id,
                snapshot_id=snapshot_id,
                opportunity_id=opportunity_id,
                job_id=ledger_job_id,
                failure_kind=failure_kind,
                retryable=retryable,
            )
            logger.error(
                "process_inbound_pitch_processing_failed",
                person_id=person_id,
                error_type=type(exc).__name__,
                failure_kind=failure_kind,
                retryable=retryable,
            )
            await terminalize(failure, rollback=True, phase="processing")
            raise

        if isinstance(processing_result, dict) and (
            processing_result.get("status") == "failed" or "error" in processing_result
        ):
            downstream_kind = processing_result.get("failure_kind", "permanent")
            if downstream_kind not in {"transient", "rate_limited", "permanent"}:
                downstream_kind = "permanent"
            downstream_retryable = processing_result.get("retryable", False)
            if not isinstance(downstream_retryable, bool):
                downstream_retryable = downstream_kind in {"transient", "rate_limited"}
            failure = _failure_result(
                "processing_failed",
                person_id=person_id,
                snapshot_id=snapshot_id,
                opportunity_id=opportunity_id,
                job_id=ledger_job_id,
                failure_kind=downstream_kind,
                retryable=downstream_retryable,
            )
            await terminalize(failure, phase="processing")
            return failure

        result["processing"] = processing_result
        try:
            await update_job(
                session,
                ledger_job_id,
                status="succeeded",
                phase="complete",
                attempt=job_attempt,
                progress=1.0,
                clear_error=True,
                result=result,
            )
            await session.commit()
        except Exception as exc:
            failure_kind, retryable = classify_connector_failure(exc)
            failure = _failure_result(
                "database_failure",
                person_id=person_id,
                snapshot_id=snapshot_id,
                opportunity_id=opportunity_id,
                job_id=ledger_job_id,
                failure_kind=failure_kind,
                retryable=retryable,
            )
            await terminalize(failure, rollback=True, phase="processing")
            raise

    logger.info("process_inbound_pitch_completed", person_id=person_id, job_id=ledger_job_id)
    return result
