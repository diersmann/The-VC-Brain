"""Arq job for processing inbound pitch submissions."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from app.collectors.jobs import _session_ctx
from app.collectors.queue import enqueue as queue_enqueue
from app.config import get_settings
from app.db.models import Observation, SourceSnapshot
from app.processing.pipeline_job import process_candidate_job
from app.storage import get_snapshot
from app.uploads import UploadRejected, extract_pdf_text

logger = structlog.get_logger(__name__)

async def process_inbound_pitch_job(
    ctx: dict[str, Any],
    person_id: str,
    snapshot_id: str,
    opportunity_id: str,
    company_name: str
) -> dict[str, Any]:
    """Process an uploaded pitch deck.
    
    Extracts text, creates generic observations, and then enqueues
    the processing pipeline and memo generation.
    """
    logger.info("process_inbound_pitch_started", person_id=person_id, snapshot_id=snapshot_id)

    async with _session_ctx(ctx) as session:
        # Get the snapshot
        snapshot = await session.get(SourceSnapshot, uuid.UUID(snapshot_id))
        if not snapshot:
            logger.error("snapshot_not_found", snapshot_id=snapshot_id)
            return {"error": "snapshot_not_found"}

        # Fetch PDF content from MinIO
        content = await get_snapshot(snapshot.storage_path)
        
        try:
            settings = get_settings()
            text_content = await asyncio.to_thread(
                extract_pdf_text,
                content,
                max_pages=settings.upload_max_pages,
                max_text_chars=settings.upload_max_text_chars,
            )
        except UploadRejected as exc:
            logger.warning("pdf_extraction_rejected", error=str(exc), snapshot_id=snapshot_id)
            return {"error": "pdf_rejected", "snapshot_id": snapshot_id}

        # Create observations
        now = datetime.now(UTC)
        observations_to_add = []
        
        # We store the raw text as an observation so the reconciler/LLM can use it
        observations_to_add.append(
            Observation(
                snapshot_id=snapshot.id,
                subject_id=uuid.UUID(person_id),
                predicate="pitch_deck_text",
                object_value=text_content[:50000], # truncate to 50k chars
                observed_at=now,
                extractor_version="inbound-v1",
                confidence=1.0
            )
        )
        
        # Store company name as observation
        observations_to_add.append(
            Observation(
                snapshot_id=snapshot.id,
                subject_id=uuid.UUID(person_id),
                predicate="company_name",
                object_value=company_name,
                observed_at=now,
                extractor_version="inbound-v1",
                confidence=1.0
            )
        )

        session.add_all(observations_to_add)
        await session.commit()
        
    # Now that we have observations, we run the standard candidate processing pipeline
    # We can just call it directly since we're in a job already
    await process_candidate_job(ctx, person_id)
    
    # Finally, enqueue the memo generation job
    await queue_enqueue(
        ctx["redis"],
        {
            "job_type": "generate_memo",
            "person_id": person_id,
            "opportunity_id": opportunity_id
        },
        priority=100
    )

    logger.info("process_inbound_pitch_completed", person_id=person_id)
    return {"status": "success", "person_id": person_id, "snapshot_id": snapshot_id}
