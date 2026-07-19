"""Merge logic — merges two Person records into one canonical Person.

When a match is confirmed (auto-merge or human-approved), the duplicate
Person is marked as superseded and all its data is reassigned to the
canonical Person.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Observation,
    OpportunityFounder,
    Person,
    Relationship,
    ScoreSnapshot,
)

logger = structlog.get_logger(__name__)


async def merge_persons(
    session: AsyncSession,
    canonical_id: uuid.UUID,
    duplicate_id: uuid.UUID,
    confidence: float,
    reasons: list[str],
) -> Person:
    """Merge *duplicate_id* into *canonical_id*.

    Steps:
        1. Load both persons.
        2. Merge handles (union of both dicts).
        3. Merge display_name (prefer canonical's, fall back to longer).
        4. Merge email (prefer non-null).
        5. Reassign Observations, Relationships, ScoreSnapshots,
           OpportunityFounders from duplicate → canonical.
        6. Mark duplicate as superseded.

    Returns the canonical Person (with updated handles/name/email).
    """
    canonical = await session.get(Person, canonical_id)
    duplicate = await session.get(Person, duplicate_id)

    if not canonical or not duplicate:
        msg = f"Person not found: canonical={canonical_id} duplicate={duplicate_id}"
        raise ValueError(msg)

    if not duplicate.canonical:
        logger.warning("duplicate_already_superseded", person_id=str(duplicate_id))
        return canonical

    now = datetime.now(UTC)

    # 1. Merge handles
    merged_handles: dict[str, str] = dict(canonical.handles or {})
    if duplicate.handles:
        for source, handle in duplicate.handles.items():
            if source not in merged_handles:
                merged_handles[source] = handle
    canonical.handles = merged_handles

    # 2. Merge display_name
    if not canonical.display_name and duplicate.display_name:
        canonical.display_name = duplicate.display_name
    elif (
        canonical.display_name
        and duplicate.display_name
        and len(duplicate.display_name) > len(canonical.display_name)
    ):
        # Prefer the longer, more specific name
        canonical.display_name = duplicate.display_name

    # 3. Merge email
    if not canonical.email and duplicate.email:
        canonical.email = duplicate.email

    # 4. Reassign Observations
    await session.execute(
        update(Observation)
        .where(Observation.subject_id == duplicate_id)
        .values(subject_id=canonical_id)
    )

    # 5. Reassign Relationships (skip self-relationships)
    await session.execute(
        update(Relationship)
        .where(Relationship.person_a_id == duplicate_id)
        .values(person_a_id=canonical_id)
    )
    await session.execute(
        update(Relationship)
        .where(Relationship.person_b_id == duplicate_id)
        .values(person_b_id=canonical_id)
    )

    # Delete any self-relationships created by the merge
    self_rels = await session.execute(
        select(Relationship).where(
            (Relationship.person_a_id == canonical_id)
            & (Relationship.person_b_id == canonical_id)
        )
    )
    for rel in self_rels.scalars().all():
        await session.delete(rel)

    # 6. Reassign ScoreSnapshots
    await session.execute(
        update(ScoreSnapshot)
        .where(ScoreSnapshot.subject_id == duplicate_id)
        .values(subject_id=canonical_id)
    )

    # 7. Reassign OpportunityFounders
    await session.execute(
        update(OpportunityFounder)
        .where(OpportunityFounder.person_id == duplicate_id)
        .values(person_id=canonical_id)
    )

    # 8. Mark duplicate as superseded
    duplicate.canonical = False
    duplicate.superseded_by_id = canonical_id
    duplicate.merged_at = now

    await session.flush()

    logger.info(
        "person_merged",
        canonical_id=str(canonical_id),
        duplicate_id=str(duplicate_id),
        confidence=confidence,
        reasons=reasons,
        merged_handles=list(merged_handles.keys()),
    )

    return canonical
