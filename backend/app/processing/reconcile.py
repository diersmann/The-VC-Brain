"""Reconcile raw observations into Claims.

Groups observations by predicate, resolves contradictions (stronger
evidence wins, weaker is linked as counter_evidence), and writes Claim
rows.  Never silently drops the unfavorable observation — both sides
are retained (per architecture doc §Claim-Level Trust Score).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Claim, Observation

logger = structlog.get_logger(__name__)


def _observation_strength(obs: Observation) -> float:
    """Higher is stronger. Combines confidence and recency."""
    confidence = obs.confidence if obs.confidence else 0.5
    # Recency boost: newer observations are slightly stronger
    age_days = (datetime.now(UTC) - obs.observed_at).days if obs.observed_at else 999
    recency = max(0.5, 1.0 - age_days / 365)
    return confidence * recency


async def reconcile_observations(
    session: AsyncSession,
    person_id: uuid.UUID,
) -> int:
    """Reconcile all observations for a person into Claims.

    Returns the number of claims created.
    """
    result = await session.execute(
        select(Observation)
        .where(Observation.subject_id == person_id)
        .order_by(Observation.observed_at.desc())
    )
    observations: list[Observation] = list(result.scalars().all())

    if not observations:
        return 0

    # Group by predicate
    by_predicate: dict[str, list[Observation]] = {}
    for obs in observations:
        by_predicate.setdefault(obs.predicate, []).append(obs)

    claims_created = 0

    for predicate, group in by_predicate.items():
        if len(group) == 1:
            # Single observation → unverified claim
            obs = group[0]
            claim = Claim(
                observation_ids=[str(obs.id)],
                subject_id=person_id,
                predicate=predicate,
                object_value=obs.object_value,
                status="unverified",
                confidence=obs.confidence,
                valid_time_start=obs.observed_at,
            )
            session.add(claim)
            claims_created += 1
        else:
            # Multiple observations for the same predicate
            # Check if they agree or contradict
            values = {obs.object_value.strip() for obs in group}
            if len(values) == 1:
                # All agree → supported claim
                strongest = max(group, key=_observation_strength)
                claim = Claim(
                    observation_ids=[str(o.id) for o in group],
                    subject_id=person_id,
                    predicate=predicate,
                    object_value=strongest.object_value,
                    status="supported",
                    confidence=max(o.confidence for o in group),
                    valid_time_start=strongest.observed_at,
                )
                session.add(claim)
                claims_created += 1
            else:
                # Contradiction — stronger evidence wins, weaker becomes
                # counter_evidence.  Both are retained.
                sorted_obs = sorted(group, key=_observation_strength, reverse=True)
                winner = sorted_obs[0]
                losers = sorted_obs[1:]

                # Check for existing claim to supersede
                existing_result = await session.execute(
                    select(Claim).where(
                        Claim.subject_id == person_id,
                        Claim.predicate == predicate,
                    ).order_by(Claim.created_at.desc()).limit(1)
                )
                existing = existing_result.scalar_one_or_none()

                claim = Claim(
                    observation_ids=[str(winner.id)],
                    subject_id=person_id,
                    predicate=predicate,
                    object_value=winner.object_value,
                    status="contradicted",
                    confidence=winner.confidence,
                    valid_time_start=winner.observed_at,
                    supersession_id=existing.id if existing else None,
                )
                session.add(claim)
                claims_created += 1

                # Write counter-evidence claims for the losers
                for loser in losers:
                    counter_claim = Claim(
                        observation_ids=[str(loser.id)],
                        subject_id=person_id,
                        predicate=predicate,
                        object_value=loser.object_value,
                        status="contradicted",
                        confidence=loser.confidence,
                        valid_time_start=loser.observed_at,
                    )
                    session.add(counter_claim)
                    claims_created += 1

    await session.flush()
    logger.info(
        "observations_reconciled",
        person_id=str(person_id),
        observations=len(observations),
        claims_created=claims_created,
    )
    return claims_created