import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import structlog
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import InboundSubmission, JobRun, OutboxEvent, Person, SourceSnapshot
from app.db.session import get_session
from app.opportunity_service import create_inbound_opportunity, record_channel_touch
from app.outbox import inbound_outbox_event
from app.source_policy import build_source_use_policy
from app.storage import put_snapshot
from app.uploads import UploadRejected, quarantine_pitch_upload

router = APIRouter(prefix="/inbound", tags=["inbound"])
logger = structlog.get_logger(__name__)


class InboundPitchResponse(BaseModel):
    status: str
    person_id: str
    opportunity_id: str
    job_id: str | None = None


_FOUNDER_EVIDENCE_LIMITS = {
    "work_sample_url": 2048,
    "work_sample_description": 4000,
    "learning_velocity": 4000,
    "reference_context": 4000,
    "interview_context": 4000,
}


def _founder_evidence(values: dict[str, str | None]) -> dict[str, str]:
    """Normalize optional direct-work evidence without requiring public history."""
    evidence: dict[str, str] = {}
    for field, raw_value in values.items():
        value = (raw_value or "").strip()
        if not value:
            continue
        limit = _FOUNDER_EVIDENCE_LIMITS[field]
        if len(value) > limit:
            raise HTTPException(status_code=400, detail=f"{field} exceeds {limit} characters")
        if field == "work_sample_url":
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise HTTPException(
                    status_code=400, detail="work_sample_url must be an HTTP(S) URL"
                )
        evidence[field] = value
    return evidence


async def _get_redis() -> ArqRedis:
    """Create a Redis pool for callers that need direct job enqueueing."""
    settings = get_settings()
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))


async def _enqueue_inbound_pitch(
    redis: ArqRedis,
    *,
    person_id: str,
    snapshot_id: str,
    opportunity_id: str,
    company_name: str,
    founder_evidence: dict[str, str] | None = None,
    job_id: str | None = None,
) -> None:
    """Enqueue inbound processing and always release the temporary Redis pool."""
    try:
        kwargs: dict[str, Any] = {
            "person_id": person_id,
            "snapshot_id": snapshot_id,
            "opportunity_id": opportunity_id,
            "company_name": company_name,
        }
        if founder_evidence is not None:
            kwargs["founder_evidence"] = founder_evidence
        if job_id is not None:
            kwargs["job_id"] = job_id
        await redis.enqueue_job("process_inbound_pitch_job", **kwargs, _queue_name="arq:queue")
    finally:
        await redis.aclose()


@router.post("/pitch")
async def submit_pitch(
    founder_name: str = Form(...),
    founder_email: str = Form(...),
    company_name: str = Form(...),
    file: UploadFile = File(...),  # noqa: B008
    work_sample_url: str | None = Form(None),
    work_sample_description: str | None = Form(None),
    learning_velocity: str | None = Form(None),
    reference_context: str | None = Form(None),
    interview_context: str | None = Form(None),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> InboundPitchResponse:
    logger.info("inbound_pitch_received", company=company_name)

    idempotency_key = idempotency_key.strip()
    if not 1 <= len(idempotency_key) <= 128:
        raise HTTPException(status_code=400, detail="Idempotency-Key must be 1-128 characters")
    founder_evidence = _founder_evidence(
        {
            "work_sample_url": work_sample_url,
            "work_sample_description": work_sample_description,
            "learning_velocity": learning_velocity,
            "reference_context": reference_context,
            "interview_context": interview_context,
        }
    )

    existing_result = await db.execute(
        select(InboundSubmission).where(InboundSubmission.idempotency_key == idempotency_key)
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        existing_job_id: str | None = None
        event_result = await db.execute(
            select(OutboxEvent).where(
                OutboxEvent.dedupe_key == f"inbound-submission:{idempotency_key}"
            )
        )
        event = event_result.scalar_one_or_none()
        if event is not None:
            raw_payload = getattr(event, "payload", None)
            payload = raw_payload if isinstance(raw_payload, dict) else {}
            kwargs = payload.get("kwargs", {})
            if isinstance(kwargs, dict) and kwargs.get("job_id") is not None:
                existing_job_id = str(kwargs["job_id"])
        return InboundPitchResponse(
            status=existing.status,
            person_id=str(existing.person_id),
            opportunity_id=str(existing.opportunity_id),
            job_id=existing_job_id,
        )

    try:
        content = await quarantine_pitch_upload(file, get_settings())
    except UploadRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Store only after quarantine and validation.
    content_hash, storage_path = await put_snapshot(
        content=content,
        content_type="application/pdf",
        source_type="inbound_deck",
    )

    snapshot = SourceSnapshot(
        uri=f"inbound://{file.filename}",
        source_type="inbound_deck",
        content_hash=content_hash,
        storage_path=storage_path,
        collected_at=datetime.now(UTC),
        source_use_policy=build_source_use_policy(
            "inbound_deck", {"source": "founder-provided", "model_use": "allowed"}
        ),
    )
    db.add(snapshot)

    # Use email as the stable identifier for an inbound founder.
    stable_id = f"email:{founder_email.lower().strip()}"
    result = await db.execute(select(Person).where(Person.stable_id == stable_id))
    person = result.scalar_one_or_none()

    if not person:
        person = Person(
            stable_id=stable_id,
            display_name=founder_name,
            email=founder_email,
            handles={"email": founder_email},
            consent_state="pending",
        )
        db.add(person)
        await db.flush()

    opportunity = await create_inbound_opportunity(db, person, company_name=company_name)
    await db.flush()
    record_channel_touch(
        db,
        opportunity.id,
        "inbound_application",
        "application_received",
        source_ref=str(snapshot.id),
        metadata={"source_type": "founder_submission"},
    )

    submission = InboundSubmission(
        idempotency_key=idempotency_key,
        person_id=person.id,
        opportunity_id=opportunity.id,
        snapshot_id=snapshot.id,
        status="accepted",
        founder_evidence=founder_evidence,
    )
    db.add(submission)
    # Generate and add the ID before the one submission transaction commits.
    # Avoid an intermediate flush: a concurrent idempotency race must be
    # handled by the IntegrityError re-read below rather than escaping here.
    processing_job = JobRun(
        id=uuid.uuid4(),
        job_type="process_inbound_pitch",
        status="queued",
        phase="queued",
    )
    db.add(processing_job)
    # Dispatch is durable through the outbox after commit; do not enqueue the
    # same job directly here, which would duplicate processing.
    db.add(inbound_outbox_event(submission, company_name, job_id=str(processing_job.id)))

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing_result = await db.execute(
            select(InboundSubmission).where(InboundSubmission.idempotency_key == idempotency_key)
        )
        existing = existing_result.scalar_one_or_none()
        if existing is None:
            raise
        race_job_id: str | None = None
        event_result = await db.execute(
            select(OutboxEvent).where(
                OutboxEvent.dedupe_key == f"inbound-submission:{idempotency_key}"
            )
        )
        event = event_result.scalar_one_or_none()
        if event is not None:
            raw_payload = getattr(event, "payload", None)
            payload = raw_payload if isinstance(raw_payload, dict) else {}
            kwargs = payload.get("kwargs", {})
            if isinstance(kwargs, dict) and kwargs.get("job_id") is not None:
                race_job_id = str(kwargs["job_id"])
        return InboundPitchResponse(
            status=existing.status,
            person_id=str(existing.person_id),
            opportunity_id=str(existing.opportunity_id),
            job_id=race_job_id,
        )

    return InboundPitchResponse(
        status=submission.status,
        person_id=str(submission.person_id),
        opportunity_id=str(submission.opportunity_id),
        job_id=str(processing_job.id),
    )
