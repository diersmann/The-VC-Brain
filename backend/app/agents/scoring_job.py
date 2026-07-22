"""Arq job for multi-agent candidate scoring."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select

from app.agents.scoring import build_evidence_text, score_candidate
from app.collectors.jobs import _session_ctx
from app.db.models import (
    Assessment,
    Observation,
    Person,
    ScoreSnapshot,
)

logger = structlog.get_logger(__name__)

_RATING_BUCKETS = [
    (67.0, "bullish"),
    (34.0, "neutral"),
    (0.0, "bear"),
]


def _rating(score: float) -> str:
    for threshold, label in _RATING_BUCKETS:
        if score >= threshold:
            return label
    return "bear"


async def score_candidate_job(ctx: dict[str, Any], person_id: str) -> dict[str, Any]:
    """Run the multi-agent scoring committee for one candidate.

    Builds the evidence package from all observations, runs the 3 specialist
    agents + critic + aggregator, writes Assessments and a ScoreSnapshot.
    """
    from app.config import get_settings

    settings = ctx.get("settings") or get_settings()
    logger.info("score_candidate_job_started", person_id=person_id)

    async with _session_ctx(ctx) as session:
        person = await session.get(Person, uuid.UUID(person_id))
        if person is None:
            logger.error("score_candidate_person_not_found", person_id=person_id)
            return {"error": "person_not_found"}

        if not person.canonical:
            logger.warning("score_candidate_not_canonical", person_id=person_id)
            return {"error": "person_not_canonical"}

        # Fetch all observations for the person
        result = await session.execute(
            select(Observation)
            .where(Observation.subject_id == person.id)
            .order_by(Observation.observed_at.desc())
            .limit(500)
        )
        observations: list[Observation] = list(result.scalars().all())

        if not observations:
            logger.warning("score_candidate_no_observations", person_id=person_id)
            return {"error": "no_observations"}

        # Build evidence package
        evidence_text, obs_ids = build_evidence_text(observations, person)

        # Run the scoring committee
        scorecard, _metadata = await score_candidate(
            evidence_text=evidence_text,
            api_key=settings.llm_api_key,
            model=settings.agent_model,
            concurrency=settings.agent_concurrency,
        )

        # Find or create an Opportunity for this person
        from app.opportunity_service import get_or_create_opportunity

        opportunity = await get_or_create_opportunity(
            session, person, source_kind="outbound", lifecycle_state="investigating",
        )

        # Write 3 Assessment rows (one per axis)
        for dim_name, score_val in [
            ("execution", scorecard.execution),
            ("technical", scorecard.technical),
            ("commercial", scorecard.commercial),
        ]:
            agent_assessment = scorecard.agents.get(dim_name)
            if agent_assessment is None:
                continue
            session.add(
                Assessment(
                    opportunity_id=opportunity.id,
                    axis=dim_name,
                    rating=_rating(score_val),
                    trend="stable",
                    confidence=agent_assessment.confidence,
                    evidence_ids=agent_assessment.evidence,
                    counter_evidence_ids=agent_assessment.counter_evidence,
                    unknowns=agent_assessment.unknowns,
                )
            )

        # Write the final ScoreSnapshot
        score_components: dict[str, object] = {
            "founder": scorecard.composite / 100.0,  # 0-1 scale for candidates API
            "execution": scorecard.execution,
            "technical": scorecard.technical,
            "commercial": scorecard.commercial,
            "evidence_confidence": scorecard.confidence,
            "hard_eligible": scorecard.hard_eligible,
            "critique": [i.model_dump() for i in scorecard.critique],
            "agents": {dim: a.model_dump() for dim, a in scorecard.agents.items()},
        }

        session.add(
            ScoreSnapshot(
                subject_id=person.id,
                subject_type="person",
                rubric_version="founder-agent-v1",
                components=score_components,
                confidence_interval={
                    "composite": {
                        "low": round(
                            max(0.0, scorecard.composite - (1 - scorecard.confidence) * 10), 2
                        ),
                        "high": round(
                            min(100.0, scorecard.composite + (1 - scorecard.confidence) * 10), 2
                        ),
                    }
                },
                evidence_ids=obs_ids[:50],  # cap to avoid huge rows
            )
        )

        await session.commit()

    logger.info(
        "score_candidate_job_completed",
        person_id=person_id,
        composite=scorecard.composite,
        confidence=scorecard.confidence,
        model=settings.agent_model,
    )

    return {
        "person_id": person_id,
        "composite": scorecard.composite,
        "confidence": scorecard.confidence,
        "hard_eligible": scorecard.hard_eligible,
        "model": settings.agent_model,
    }