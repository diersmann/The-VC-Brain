"""Deduplicate Claims using embedding similarity."""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Claim, Observation

logger = structlog.get_logger(__name__)

# Cosine similarity threshold for near-duplicate detection
_DUPLICATE_THRESHOLD = 0.92


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


async def deduplicate_claims(
    session: AsyncSession,
    person_id: uuid.UUID,
) -> int:
    """Find and merge near-duplicate claims using embedding similarity.

    Returns the number of claims deduplicated.
    """
    result = await session.execute(
        select(Claim).where(
            Claim.subject_id == person_id,
            Claim.supersession_id.is_(None),
        ).order_by(Claim.created_at.desc())
    )
    claims: list[Claim] = list(result.scalars().all())

    if len(claims) < 2:
        return 0

    # Fetch embeddings for the observations backing each claim
    claim_embeddings: dict[uuid.UUID, list[float] | None] = {}
    for claim in claims:
        if not claim.observation_ids:
            claim_embeddings[claim.id] = None
            continue
        obs_id = claim.observation_ids[0]
        obs_result = await session.execute(
            select(Observation).where(Observation.id == uuid.UUID(obs_id))
        )
        obs = obs_result.scalar_one_or_none()
        claim_embeddings[claim.id] = getattr(obs, "embedding", None) if obs else None

    deduplicated = 0
    superseded: set[uuid.UUID] = set()

    for i, claim_a in enumerate(claims):
        if claim_a.id in superseded:
            continue
        emb_a = claim_embeddings.get(claim_a.id)
        if not emb_a:
            continue

        for j in range(i + 1, len(claims)):
            claim_b = claims[j]
            if claim_b.id in superseded:
                continue
            if claim_b.predicate != claim_a.predicate:
                continue

            emb_b = claim_embeddings.get(claim_b.id)
            if not emb_b:
                continue

            similarity = _cosine_similarity(emb_a, emb_b)
            if similarity >= _DUPLICATE_THRESHOLD:
                # claim_b is a near-duplicate of claim_a; supersede it
                claim_b.supersession_id = claim_a.id
                superseded.add(claim_b.id)
                deduplicated += 1

    await session.flush()
    if deduplicated:
        logger.info(
            "claims_deduplicated",
            person_id=str(person_id),
            deduplicated=deduplicated,
            total_claims=len(claims),
        )
    return deduplicated