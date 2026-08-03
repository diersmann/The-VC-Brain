"""Arq job for processing inbound pitch submissions."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from app.collectors.jobs import _session_ctx
from app.config import get_settings
from app.db.models import Observation, SourceSnapshot
from app.processing.pipeline_job import process_candidate_job
from app.storage import get_snapshot
from app.uploads import UploadRejected, extract_pdf_pages

logger = structlog.get_logger(__name__)

async def process_inbound_pitch_job(
    ctx: dict[str, Any],
    person_id: str,
    snapshot_id: str,
    opportunity_id: str,
    company_name: str
) -> dict[str, Any]:
    """Process an uploaded pitch deck.
    
    Extracts text and runs the generic processing pipeline. The lifecycle
    worker schedules Founder Score, opportunity research, and memo generation
    only after their required upstream outputs exist.
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
            page_text = await asyncio.to_thread(
                extract_pdf_pages,
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
        
        # Store company name as observation
        observations_to_add.append(
            Observation(
                snapshot_id=snapshot.id,
                subject_id=uuid.UUID(person_id),
                opportunity_id=uuid.UUID(opportunity_id),
                predicate="company_name",
                object_value=company_name,
                observed_at=now,
                extractor_version="inbound-v1",
                confidence=1.0
            )
        )

        session.add_all(observations_to_add)
        await session.commit()
        
    # Run processing before the lifecycle worker evaluates this opportunity.
    # Memo generation is intentionally not queued here: it must be gated on
    # the Founder Score, all three opportunity axes, and scoped accepted claims.
    processing_result = await process_candidate_job(ctx, person_id)

    logger.info("process_inbound_pitch_completed", person_id=person_id)
    return {
        "status": "success",
        "person_id": person_id,
        "snapshot_id": snapshot_id,
        "opportunity_id": opportunity_id,
        "processing": processing_result,
        "next_stage": "inbound_triage",
    }
