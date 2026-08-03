"""Reconcile raw observations into idempotent Claims.

Groups observations by predicate and opportunity, resolves contradictions
without dropping unfavorable evidence, and treats ``Claim.supersession_id``
as the newer claim that supersedes the current row.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifact_provenance import build_artifact_metadata, fingerprint_payload
from app.db.models import Claim, ClaimObservationLink, Observation

logger = structlog.get_logger(__name__)

_TRUST_VERSION = "claim-trust-v1"
_SOURCE_AUTHORITY = {
    "inbound": 0.9,
    "public": 0.8,
    "github": 0.7,
    "producthunt": 0.5,
    "hackernews": 0.4,
    "tavily": 0.3,
}


def _trust_for_observations(
    observations: list[Observation], *, contradicted: bool
) -> tuple[float, dict[str, object], dict[str, float], str]:
    """Calculate a versioned, conservative claim Trust artifact."""
    source_kinds = {
        (obs.extractor_version or "unknown").split("-", maxsplit=1)[0].lower()
        for obs in observations
    }
    authority = sum(_SOURCE_AUTHORITY.get(kind, 0.5) for kind in source_kinds) / max(
        1, len(source_kinds)
    )
    directness = 0.8 if source_kinds.intersection({"inbound", "github", "public"}) else 0.5
    independence = min(1.0, len(source_kinds) / 2)
    corroboration = min(1.0, len(observations) / 3)
    now = datetime.now(UTC)
    freshness = sum(
        max(0.5, 1.0 - max(0, (now - obs.observed_at).days) / 365)
        for obs in observations
    ) / max(1, len(observations))
    extraction = sum(max(0.0, min(1.0, obs.confidence)) for obs in observations) / max(
        1, len(observations)
    )
    identity = 0.5
    contradiction_penalty = 0.2 if contradicted else 0.0
    score = max(
        0.0,
        min(
            1.0,
            0.2 * authority
            + 0.1 * directness
            + 0.1 * independence
            + 0.15 * corroboration
            + 0.15 * freshness
            + 0.2 * extraction
            + 0.1 * identity
            - contradiction_penalty,
        ),
    )
    width = max(0.1, 0.35 - 0.2 * extraction - 0.1 * corroboration)
    interval = {
        "low": round(max(0.0, score - width), 4),
        "high": round(min(1.0, score + width), 4),
    }
    components: dict[str, object] = {
        "source_authority": round(authority, 4),
        "directness": round(directness, 4),
        "independence": round(independence, 4),
        "corroboration": round(corroboration, 4),
        "freshness": round(freshness, 4),
        "extraction_confidence": round(extraction, 4),
        "identity_confidence": identity,
        "contradiction_penalty": contradiction_penalty,
        "observation_count": len(observations),
    }
    explanation = (
        f"Trust {score:.2f} from authority, directness, independence, corroboration, "
        f"freshness, extraction confidence, and an explicit unknown identity confidence "
        f"of {identity:.2f}."
    )
    if contradicted:
        explanation += " Contradiction penalty applied; counter-evidence remains visible."
    return round(score, 4), components, interval, explanation


def _apply_trust(claim: Claim, observations: list[Observation], *, contradicted: bool) -> None:
    score, components, interval, explanation = _trust_for_observations(
        observations, contradicted=contradicted
    )
    claim.trust_version = _TRUST_VERSION
    claim.trust_score = score
    claim.trust_components = components
    claim.trust_interval = interval
    claim.trust_explanation = explanation


def _observation_strength(obs: Observation) -> float:
    """Higher is stronger. Combines confidence and recency."""
    confidence = obs.confidence if obs.confidence else 0.5
    # Recency boost: newer observations are slightly stronger
    age_days = (datetime.now(UTC) - obs.observed_at).days if obs.observed_at else 999
    recency = max(0.5, 1.0 - age_days / 365)
    return confidence * recency


def _claim_matches(
    claim: Claim,
    *,
    predicate: str,
    object_value: str,
    status: str,
    observation_ids: list[str],
) -> bool:
    """Return whether a claim is the deterministic output for this input set."""
    return (
        claim.predicate == predicate
        and claim.object_value.strip() == object_value.strip()
        and claim.status == status
        and list(claim.observation_ids) == observation_ids
    )


def _find_matching_claim(
    claims: list[Claim],
    *,
    predicate: str,
    object_value: str,
    status: str,
    observation_ids: list[str],
) -> Claim | None:
    for claim in claims:
        if _claim_matches(
            claim,
            predicate=predicate,
            object_value=object_value,
            status=status,
            observation_ids=observation_ids,
        ):
            return claim
    return None


def _close_superseded_claims(
    claims: list[Claim],
    replacement: Claim,
    *,
    predicate: str,
) -> None:
    """Point prior current claims at their newer replacement and close validity."""
    for previous in claims:
        if previous.id == replacement.id or previous.predicate != predicate:
            continue
        if previous.supersession_id is not None:
            continue
        previous.supersession_id = replacement.id
        previous.valid_time_end = replacement.valid_time_start


def _link_claim_observations(session: AsyncSession, claim: Claim) -> None:
    """Write FK-backed links while retaining the legacy JSON evidence list."""
    for observation_id in claim.observation_ids:
        session.add(
            ClaimObservationLink(
                claim_id=claim.id,
                observation_id=uuid.UUID(str(observation_id)),
            )
        )


def _claim_artifact_metadata(
    *,
    run_id: uuid.UUID,
    observation_ids: list[str],
    predicate: str,
    opportunity_id: uuid.UUID | None,
) -> dict[str, object]:
    """Describe deterministic reconciliation inputs for a newly derived claim."""
    return build_artifact_metadata(
        run_id=run_id,
        artifact_type="claim",
        code_version="reconcile-v2",
        input_fingerprint=fingerprint_payload(sorted(observation_ids)),
        parameters={
            "predicate": predicate,
            "opportunity_id": str(opportunity_id) if opportunity_id else None,
        },
    )


async def reconcile_observations(
    session: AsyncSession,
    person_id: uuid.UUID,
) -> int:
    """Reconcile all observations for a person into Claims.

    Existing deterministic claim outputs are reused, so rerunning the same
    observations creates zero rows. Returns the number of claims created.
    """
    result = await session.execute(
        select(Observation)
        .where(Observation.subject_id == person_id)
        .order_by(Observation.observed_at.desc(), Observation.id.desc())
    )
    observations: list[Observation] = list(result.scalars().all())

    if not observations:
        return 0

    run_id = uuid.uuid4()
    claims_result = await session.execute(select(Claim).where(Claim.subject_id == person_id))
    existing_claims: list[Claim] = list(claims_result.scalars().all())

    # Group by predicate and opportunity. Evidence without an opportunity is
    # kept in its own explicit provenance gap and cannot cross-contaminate an
    # opportunity-scoped claim.
    by_predicate: dict[tuple[str, uuid.UUID | None], list[Observation]] = {}
    for obs in observations:
        by_predicate.setdefault((obs.predicate, obs.opportunity_id), []).append(obs)

    claims_created = 0

    for (predicate, opportunity_id), group in by_predicate.items():
        scoped_claims = [
            claim for claim in existing_claims if claim.opportunity_id == opportunity_id
        ]
        if len(group) == 1:
            obs = group[0]
            observation_ids = [str(obs.id)]
            if _find_matching_claim(
                scoped_claims,
                predicate=predicate,
                object_value=obs.object_value,
                status="unverified",
                observation_ids=observation_ids,
            ):
                continue
            claim = Claim(
                observation_ids=observation_ids,
                artifact_metadata=_claim_artifact_metadata(
                    run_id=run_id,
                    observation_ids=observation_ids,
                    predicate=predicate,
                    opportunity_id=opportunity_id,
                ),
                subject_id=person_id,
                opportunity_id=opportunity_id,
                predicate=predicate,
                object_value=obs.object_value,
                status="unverified",
                confidence=obs.confidence,
                valid_time_start=obs.observed_at,
            )
            _apply_trust(claim, [obs], contradicted=False)
            session.add(claim)
            await session.flush()
            _link_claim_observations(session, claim)
            existing_claims.append(claim)
            claims_created += 1
            continue

        values = {obs.object_value.strip() for obs in group}
        if len(values) == 1:
            strongest = max(group, key=_observation_strength)
            observation_ids = [str(o.id) for o in group]
            if _find_matching_claim(
                scoped_claims,
                predicate=predicate,
                object_value=strongest.object_value,
                status="supported",
                observation_ids=observation_ids,
            ):
                continue
            claim = Claim(
                observation_ids=observation_ids,
                artifact_metadata=_claim_artifact_metadata(
                    run_id=run_id,
                    observation_ids=observation_ids,
                    predicate=predicate,
                    opportunity_id=opportunity_id,
                ),
                subject_id=person_id,
                opportunity_id=opportunity_id,
                predicate=predicate,
                object_value=strongest.object_value,
                status="supported",
                confidence=max(o.confidence for o in group),
                valid_time_start=strongest.observed_at,
            )
            _apply_trust(claim, group, contradicted=False)
            session.add(claim)
            await session.flush()
            _link_claim_observations(session, claim)
            _close_superseded_claims(scoped_claims, claim, predicate=predicate)
            existing_claims.append(claim)
            claims_created += 1
            continue

        # Contradiction — stronger evidence wins, weaker observations remain
        # as contradicted counter-evidence claims.
        sorted_obs = sorted(group, key=_observation_strength, reverse=True)
        winner = sorted_obs[0]
        winner_ids = [str(winner.id)]
        winner_claim = _find_matching_claim(
            scoped_claims,
            predicate=predicate,
            object_value=winner.object_value,
            status="contradicted",
            observation_ids=winner_ids,
        )
        if winner_claim is None:
            winner_claim = Claim(
                observation_ids=winner_ids,
                artifact_metadata=_claim_artifact_metadata(
                    run_id=run_id,
                    observation_ids=winner_ids,
                    predicate=predicate,
                    opportunity_id=opportunity_id,
                ),
                subject_id=person_id,
                opportunity_id=opportunity_id,
                predicate=predicate,
                object_value=winner.object_value,
                status="contradicted",
                confidence=winner.confidence,
                valid_time_start=winner.observed_at,
            )
            _apply_trust(winner_claim, [winner], contradicted=True)
            session.add(winner_claim)
            await session.flush()
            _link_claim_observations(session, winner_claim)
            _close_superseded_claims(scoped_claims, winner_claim, predicate=predicate)
            existing_claims.append(winner_claim)
            scoped_claims.append(winner_claim)
            claims_created += 1

        for loser in sorted_obs[1:]:
            loser_ids = [str(loser.id)]
            if _find_matching_claim(
                scoped_claims,
                predicate=predicate,
                object_value=loser.object_value,
                status="contradicted",
                observation_ids=loser_ids,
            ):
                continue
            counter_claim = Claim(
                observation_ids=loser_ids,
                artifact_metadata=_claim_artifact_metadata(
                    run_id=run_id,
                    observation_ids=loser_ids,
                    predicate=predicate,
                    opportunity_id=opportunity_id,
                ),
                subject_id=person_id,
                opportunity_id=opportunity_id,
                predicate=predicate,
                object_value=loser.object_value,
                status="contradicted",
                confidence=loser.confidence,
                valid_time_start=loser.observed_at,
            )
            _apply_trust(counter_claim, [loser], contradicted=True)
            session.add(counter_claim)
            await session.flush()
            _link_claim_observations(session, counter_claim)
            existing_claims.append(counter_claim)
            scoped_claims.append(counter_claim)
            claims_created += 1

    logger.info(
        "observations_reconciled",
        person_id=str(person_id),
        observations=len(observations),
        claims_created=claims_created,
    )
    return claims_created
