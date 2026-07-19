"""Identity resolution orchestrator.

Finds candidate pairs of Persons that may represent the same real person,
runs matchers, and either auto-merges or flags for review.

Uses blocking (by email prefix, blog domain, name tokens) to avoid O(n²).
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Observation, Person, PersonMatch
from app.identity.matchers import match_confidence, should_auto_merge
from app.identity.merge import merge_persons

logger = structlog.get_logger(__name__)

# Minimum confidence to create a PersonMatch review entry
_REVIEW_THRESHOLD = 0.5


async def _fetch_observations(
    session: AsyncSession,
    person_id: uuid.UUID,
) -> list[dict[str, object]]:
    """Fetch all observations for a person as dicts."""
    result = await session.execute(
        select(Observation).where(Observation.subject_id == person_id)
    )
    return [
        {
            "predicate": obs.predicate,
            "object_value": obs.object_value,
        }
        for obs in result.scalars().all()
    ]


async def _build_blocking_keys(
    session: AsyncSession,
    person_id: uuid.UUID,
) -> set[str]:
    """Build blocking keys for a person.

    A blocking key is a string that groups candidate pairs for comparison.
    Two persons are only compared if they share at least one blocking key.

    Keys:
        - Email prefix (first 3 chars of local part)
        - Blog domain (normalized)
        - Twitter handle
        - First 3 chars of display_name
    """
    keys: set[str] = set()
    obs = await _fetch_observations(session, person_id)

    for o in obs:
        pred = str(o.get("predicate", ""))
        val = str(o.get("object_value", ""))

        if pred == "email" and "@" in val:
            local = val.split("@")[0].lower()[:3]
            if local:
                keys.add(f"email:{local}")

        elif pred == "twitter_handle" and val:
            keys.add(f"twitter:{val.strip().lower()}")

        elif pred in ("blog_url", "website_url") and val:
            from app.identity.matchers import _normalize_url

            domain = _normalize_url(val).split("/")[0]
            if domain:
                keys.add(f"domain:{domain}")

        elif pred == "display_name" and val:
            tokens = val.strip().lower().split()
            for token in tokens:
                if len(token) >= 3:
                    keys.add(f"name:{token[:3]}")

    return keys


async def resolve_identities(
    session: AsyncSession,
    redis: Any,
) -> dict[str, int]:
    """Run identity resolution across all canonical persons.

    Returns a summary dict with counts of pairs evaluated, auto-merged,
    and flagged for review.
    """
    # Fetch all canonical persons
    result = await session.execute(
        select(Person).where(Person.canonical == True)  # noqa: E712
    )
    persons: list[Person] = list(result.scalars().all())

    if len(persons) < 2:
        return {"pairs_evaluated": 0, "auto_merged": 0, "flagged_for_review": 0}

    # Build blocking keys for each person
    person_keys: dict[uuid.UUID, set[str]] = {}
    for p in persons:
        person_keys[p.id] = await _build_blocking_keys(session, p.id)

    # Invert: key → list of person IDs
    key_to_persons: dict[str, list[uuid.UUID]] = {}
    for pid, keys in person_keys.items():
        for key in keys:
            if key not in key_to_persons:
                key_to_persons[key] = []
            key_to_persons[key].append(pid)

    # Generate candidate pairs from shared blocking keys
    candidate_pairs: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for pids in key_to_persons.values():
        if len(pids) < 2:
            continue
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                a, b = pids[i], pids[j]
                if a != b:
                    candidate_pairs.add((a, b) if a < b else (b, a))

    pairs_evaluated = 0
    auto_merged = 0
    flagged_for_review = 0

    for pid_a, pid_b in candidate_pairs:
        pairs_evaluated += 1

        # Skip if either person has already been merged in this batch
        person_a = await session.get(Person, pid_a)
        person_b = await session.get(Person, pid_b)
        if not person_a or not person_b:
            continue
        if not person_a.canonical or not person_b.canonical:
            continue

        obs_a = await _fetch_observations(session, pid_a)
        obs_b = await _fetch_observations(session, pid_b)

        confidence, reasons = match_confidence(obs_a, obs_b)

        if should_auto_merge(confidence):
            # Pick the earlier-created person as canonical
            if person_a.created_at and person_b.created_at:
                if person_a.created_at <= person_b.created_at:
                    canonical_id, duplicate_id = pid_a, pid_b
                else:
                    canonical_id, duplicate_id = pid_b, pid_a
            else:
                canonical_id, duplicate_id = pid_a, pid_b

            await merge_persons(session, canonical_id, duplicate_id, confidence, reasons)
            auto_merged += 1
            logger.info(
                "identity_auto_merged",
                canonical=str(canonical_id),
                duplicate=str(duplicate_id),
                confidence=confidence,
                reasons=reasons,
            )
        elif confidence >= _REVIEW_THRESHOLD:
            # Check if this pair is already in the review queue
            existing = await session.execute(
                select(PersonMatch).where(
                    (
                        (PersonMatch.person_a_id == pid_a)
                        & (PersonMatch.person_b_id == pid_b)
                    )
                    | (
                        (PersonMatch.person_a_id == pid_b)
                        & (PersonMatch.person_b_id == pid_a)
                    )
                ).where(PersonMatch.status == "pending")
            )
            if existing.scalar_one_or_none() is None:
                match = PersonMatch(
                    person_a_id=pid_a,
                    person_b_id=pid_b,
                    confidence=confidence,
                    reasons={"reasons": reasons},
                    status="pending",
                )
                session.add(match)
                flagged_for_review += 1
                logger.info(
                    "identity_flagged_for_review",
                    person_a=str(pid_a),
                    person_b=str(pid_b),
                    confidence=confidence,
                    reasons=reasons,
                )

    await session.flush()

    logger.info(
        "identity_resolution_completed",
        persons=len(persons),
        pairs_evaluated=pairs_evaluated,
        auto_merged=auto_merged,
        flagged_for_review=flagged_for_review,
    )

    return {
        "persons_checked": len(persons),
        "pairs_evaluated": pairs_evaluated,
        "auto_merged": auto_merged,
        "flagged_for_review": flagged_for_review,
    }
