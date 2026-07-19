"""Generate embeddings for observations using OpenAI text-embedding-3-small."""

from __future__ import annotations

import asyncio
import uuid

import structlog
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Observation

logger = structlog.get_logger(__name__)


async def generate_embedding(
    text: str,
    client: AsyncOpenAI | None,
    model: str,
    semaphore: asyncio.Semaphore,
) -> list[float] | None:
    """Generate an embedding for a single text."""
    if client is None:
        return None

    # Truncate to avoid token limits
    text = text[:8000]
    if not text.strip():
        return None

    async with semaphore:
        try:
            response = await client.embeddings.create(
                model=model,
                input=text,
            )
            return list(response.data[0].embedding)
        except Exception as exc:
            logger.warning("embedding_failed", error=str(exc))
            return None


async def embed_observations(
    session: AsyncSession,
    person_id: uuid.UUID,
    api_key: str,
    model: str = "text-embedding-3-small",
    concurrency: int = 4,
) -> int:
    """Generate embeddings for all observations of a person.

    Returns the number of embeddings generated.
    """
    client = AsyncOpenAI(api_key=api_key) if api_key else None
    if client is None:
        logger.warning("embedding_skipped_no_api_key")
        return 0

    semaphore = asyncio.Semaphore(concurrency)

    # Fetch observations without embeddings
    result = await session.execute(
        select(Observation).where(
            Observation.subject_id == person_id,
        ).order_by(Observation.observed_at.desc())
    )
    observations: list[Observation] = list(result.scalars().all())

    pending = [
        obs
        for obs in observations
        if obs.object_value and not getattr(obs, "embedding", None)
    ]
    embedded = 0
    batch_size = 50
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        texts = [obs.object_value[:8000] for obs in batch]
        async with semaphore:
            try:
                response = await client.embeddings.create(model=model, input=texts)
            except Exception as exc:
                logger.warning("embedding_batch_failed", error=str(exc), size=len(batch))
                continue
        vectors = sorted(response.data, key=lambda item: item.index)
        for obs, item in zip(batch, vectors, strict=True):
            obs.embedding = list(item.embedding)
            embedded += 1

    await session.flush()
    logger.info(
        "observations_embedded",
        person_id=str(person_id),
        embedded=embedded,
        total=len(observations),
    )
    return embedded
