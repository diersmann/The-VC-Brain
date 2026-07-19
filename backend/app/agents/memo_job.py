"""Arq job for investment memo generation."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import structlog
from sqlalchemy import select

from app.agents.memo import generate_memo
from app.agents.scoring import build_evidence_text
from app.collectors.jobs import _session_ctx
from app.db.models import (
    Assessment,
    InvestmentMemo,
    InvestmentThesis,
    Observation,
    Opportunity,
    OpportunityFounder,
    Person,
    ScoreSnapshot,
)

logger = structlog.get_logger(__name__)


async def generate_memo_job(ctx: dict[str, Any], person_id: str) -> dict[str, Any]:
    """Generate an investment memo for a candidate.

    Loads the latest agent scorecard + assessments + evidence + thesis,
    calls the memo agent, and writes an InvestmentMemo row.
    """
    from app.config import get_settings

    settings = ctx.get("settings") or get_settings()
    logger.info("generate_memo_job_started", person_id=person_id)

    async with _session_ctx(ctx) as session:
        person = await session.get(Person, uuid.UUID(person_id))
        if person is None:
            logger.error("memo_person_not_found", person_id=person_id)
            return {"error": "person_not_found"}

        # Fetch observations
        obs_result = await session.execute(
            select(Observation)
            .where(Observation.subject_id == person.id)
            .order_by(Observation.observed_at.desc())
            .limit(500)
        )
        observations: list[Observation] = list(obs_result.scalars().all())

        if not observations:
            logger.warning("memo_no_observations", person_id=person_id)
            return {"error": "no_observations"}

        # Build evidence text
        evidence_text, obs_ids = build_evidence_text(observations, person)

        # Fetch the latest agent scorecard
        score_result = await session.execute(
            select(ScoreSnapshot)
            .where(
                ScoreSnapshot.subject_id == person.id,
                ScoreSnapshot.rubric_version == "founder-agent-v1",
            )
            .order_by(ScoreSnapshot.created_at.desc())
            .limit(1)
        )
        score_snapshot = score_result.scalar_one_or_none()
        scorecard_summary = (
            json.dumps(score_snapshot.components, indent=2)
            if score_snapshot
            else "No agent scorecard available yet."
        )

        # Fetch assessments
        assessment_result = await session.execute(
            select(Assessment)
            .join(Opportunity, Opportunity.id == Assessment.opportunity_id)
            .join(OpportunityFounder, OpportunityFounder.opportunity_id == Opportunity.id)
            .where(OpportunityFounder.person_id == person.id)
            .order_by(Assessment.created_at.desc())
        )
        assessments = assessment_result.scalars().all()
        if assessments:
            scorecard_summary += "\n\nAssessments:\n" + "\n".join(
                f"- {a.axis}: {a.rating} (conf {a.confidence}) — {a.unknowns}"
                for a in assessments[:6]
            )

        # Fetch active thesis
        thesis_result = await session.execute(
            select(InvestmentThesis)
            .where(InvestmentThesis.is_active.is_(True))
            .order_by(InvestmentThesis.created_at.desc())
            .limit(1)
        )
        thesis = thesis_result.scalar_one_or_none()
        thesis_summary = (
            f"{thesis.name} ({thesis.version}) — stages: {thesis.stages}, "
            f"sectors: {thesis.sectors}, regions: {thesis.regions}"
            if thesis
            else "No active thesis."
        )

        # Find or create opportunity
        from app.opportunity_service import get_or_create_opportunity

        opportunity = await get_or_create_opportunity(
            session, person, source_kind="outbound", lifecycle_state="investigating",
        )

        # Generate memo
        semaphore = asyncio.Semaphore(settings.agent_concurrency)
        memo = await generate_memo(
            evidence_text=evidence_text,
            scorecard_summary=scorecard_summary,
            thesis_summary=thesis_summary,
            person_name=person.display_name or person.stable_id,
            api_key=settings.llm_api_key,
            model=settings.agent_model,
            semaphore=semaphore,
        )

        # Write InvestmentMemo
        all_evidence_ids = set(obs_ids)
        for section in memo.sections:
            all_evidence_ids.update(section.evidence_ids)

        session.add(
            InvestmentMemo(
                opportunity_id=opportunity.id,
                thesis_version=thesis.version if thesis else "none",
                sections={
                    "sections": [s.model_dump() for s in memo.sections],
                    "generation_mode": memo.generation_mode,
                },
                evidence_ids=list(all_evidence_ids)[:100],
                model_version=memo.model_version or settings.agent_model,
            )
        )

        await session.commit()

    logger.info(
        "generate_memo_job_completed",
        person_id=person_id,
        sections=len(memo.sections),
        mode=memo.generation_mode,
    )

    return {
        "person_id": person_id,
        "sections": len(memo.sections),
        "generation_mode": memo.generation_mode,
    }