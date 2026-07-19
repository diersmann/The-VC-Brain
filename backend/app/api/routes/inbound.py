from datetime import UTC, datetime

import structlog
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Person, SourceSnapshot
from app.db.session import get_session
from app.opportunity_service import create_inbound_opportunity
from app.storage import put_snapshot

router = APIRouter(prefix="/inbound", tags=["inbound"])
logger = structlog.get_logger(__name__)

async def _get_redis():
    settings = get_settings()
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))

@router.post("/pitch")
async def submit_pitch(
    founder_name: str = Form(...),
    founder_email: str = Form(...),
    company_name: str = Form(...),
    file: UploadFile = File(...),  # noqa: B008
    db: AsyncSession = Depends(get_session)  # noqa: B008
):
    logger.info("inbound_pitch_received", email=founder_email, company=company_name)
    
    # 1. Read file and save to MinIO
    content = await file.read()
    content_type = file.content_type or "application/pdf"
    content_hash, storage_path = await put_snapshot(
        content=content,
        content_type=content_type,
        source_type="inbound_deck"
    )
    
    # 2. Create SourceSnapshot
    snapshot = SourceSnapshot(
        uri=f"inbound://{file.filename}",
        source_type="inbound_deck",
        content_hash=content_hash,
        storage_path=storage_path,
        collected_at=datetime.now(UTC)
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
    
    await db.commit()
    
    # 5. Enqueue background job
    redis = await _get_redis()
    await redis.enqueue_job(
        "process_inbound_pitch_job",
        person_id=str(person.id),
        snapshot_id=str(snapshot.id),
        opportunity_id=str(opportunity.id),
        company_name=company_name,
        _queue_name="arq:queue"
    )
    
    return {"status": "success", "person_id": str(person.id), "opportunity_id": str(opportunity.id)}
