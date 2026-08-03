from datetime import UTC, datetime
from urllib.parse import urlparse

import structlog
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import InboundSubmission, Person, SourceSnapshot
from app.db.session import get_session
from app.opportunity_service import create_inbound_opportunity
from app.outbox import inbound_outbox_event
from app.source_policy import build_source_use_policy
from app.storage import put_snapshot
from app.uploads import UploadRejected, quarantine_pitch_upload

router = APIRouter(prefix="/inbound", tags=["inbound"])
logger = structlog.get_logger(__name__)

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
    db: AsyncSession = Depends(get_session)  # noqa: B008
) -> dict[str, str]:
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
        return {
            "status": existing.status,
            "person_id": str(existing.person_id),
            "opportunity_id": str(existing.opportunity_id),
        }

    try:
        content = await quarantine_pitch_upload(file, get_settings())
    except UploadRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # 1. Store only after quarantine and validation
    content_hash, storage_path = await put_snapshot(
        content=content,
        content_type="application/pdf",
        source_type="inbound_deck"
    )
    
    # 2. Create SourceSnapshot
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
    
    # 3. Get or Create Person (Founder)
    # Using email as stable_id for inbound
    stable_id = f"email:{founder_email.lower().strip()}"
    result = await db.execute(select(Person).where(Person.stable_id == stable_id))
    person = result.scalar_one_or_none()
    
    if not person:
        person = Person(
            stable_id=stable_id,
            display_name=founder_name,
            email=founder_email,
            handles={"email": founder_email},
            consent_state="pending"
        )
        db.add(person)
        await db.flush() # get ID
        
    # 4. Create Opportunity
    opportunity = await create_inbound_opportunity(
        db, person, company_name=company_name
    )
    await db.flush()

    submission = InboundSubmission(
        idempotency_key=idempotency_key,
        person_id=person.id,
        opportunity_id=opportunity.id,
        snapshot_id=snapshot.id,
        status="accepted",
        founder_evidence=founder_evidence,
    )
    db.add(submission)
    db.add(inbound_outbox_event(submission, company_name))

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
        return {
            "status": existing.status,
            "person_id": str(existing.person_id),
            "opportunity_id": str(existing.opportunity_id),
        }

    return {
        "status": submission.status,
        "person_id": str(submission.person_id),
        "opportunity_id": str(submission.opportunity_id),
    }
