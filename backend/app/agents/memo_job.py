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
    Claim,
    DecisionProposal,
    InvestmentMemo,
    InvestmentThesis,
    Observation,
    Opportunity,
    OpportunityFounder,
    Person,
    ScoreSnapshot,
)
from app.decision_proposal import build_decision_proposal

logger = structlog.get_logger(__name__)

_ACCEPTED_CLAIM_STATUSES = frozenset({"supported"})


def _apply_proposal_values(proposal: DecisionProposal, values: dict[str, Any]) -> None:
    """Copy the JSON-safe proposal contract onto its durable row."""
    for key, value in values.items():
        setattr(proposal, key, value)


def _claim_observation_ids(claim: Claim) -> list[uuid.UUID] | None:
    """Return valid observation IDs, rejecting malformed claim references."""
    raw_ids = claim.observation_ids if isinstance(claim.observation_ids, list) else []
    try:
        return [uuid.UUID(str(item)) for item in raw_ids]
    except (ValueError, TypeError, AttributeError):
        return None


def _claim_context(claims: list[Claim]) -> str:
    """Format accepted claims as explicit, bounded memo input context."""
    lines = ["--- accepted claims ---"]
    for claim in claims:
        observation_ids = ", ".join(claim.observation_ids)
        lines.append(
            f"[{claim.id}] {claim.predicate}: {claim.object_value[:500]} "
            f"(observations: {observation_ids})"
        )
    return "\n".join(lines)


def _contradiction_context(claims: list[Claim]) -> str:
    """Format contradicted claims as warnings, never accepted facts."""
    if not claims:
        return "Contradictions: none recorded for this opportunity."
    lines = ["Contradictions (excluded from accepted facts; resolve in diligence):"]
    for claim in claims:
        lines.append(f"- [{claim.id}] {claim.predicate}: {claim.object_value}")
    return "\n".join(lines)


async def generate_memo_job(
    ctx: dict[str, Any], person_id: str, opportunity_id: str
) -> dict[str, Any]:
    """Generate an investment memo for a candidate.

    Loads the latest agent scorecard + assessments + evidence + thesis,
    calls the memo agent, and writes an InvestmentMemo row.
    """
    from app.config import get_settings

    settings = ctx.get("settings") or get_settings()
    logger.info("generate_memo_job_started", person_id=person_id, opportunity_id=opportunity_id)

    async with _session_ctx(ctx) as session:
        person = await session.get(Person, uuid.UUID(person_id))
        if person is None:
            logger.error("memo_person_not_found", person_id=person_id)
            return {"error": "person_not_found"}

        try:
            requested_opportunity_id = uuid.UUID(opportunity_id)
        except ValueError:
            return {"error": "opportunity_id_required", "person_id": person_id}

        opportunity_result = await session.execute(
            select(Opportunity)
            .join(OpportunityFounder, OpportunityFounder.opportunity_id == Opportunity.id)
            .where(
                Opportunity.id == requested_opportunity_id,
                OpportunityFounder.person_id == person.id,
            )
        )
        opportunity = opportunity_result.scalar_one_or_none()
        if opportunity is None:
            return {"error": "opportunity_not_found", "person_id": person_id}

        # Only claims accepted by reconciliation may enter a memo. Their
        # observation references must also resolve to this exact opportunity.
        claims_result = await session.execute(
            select(Claim)
            .where(
                Claim.subject_id == person.id,
                Claim.opportunity_id == opportunity.id,
                Claim.status.in_(_ACCEPTED_CLAIM_STATUSES),
                Claim.supersession_id.is_(None),
            )
            .order_by(Claim.created_at.asc(), Claim.id.asc())
        )
        candidate_claims: list[Claim] = list(claims_result.scalars().all())
        claim_observation_ids = {
            observation_id
            for claim in candidate_claims
            for observation_id in (_claim_observation_ids(claim) or [])
        }
        if not claim_observation_ids:
            logger.warning("memo_no_accepted_claims", person_id=person_id)
            return {"error": "no_accepted_claims", "person_id": person_id}

        obs_result = await session.execute(
            select(Observation)
            .where(
                Observation.id.in_(claim_observation_ids),
                Observation.subject_id == person.id,
                Observation.opportunity_id == opportunity.id,
            )
            .order_by(Observation.observed_at.asc(), Observation.id.asc())
        )
        observations_by_id = {observation.id: observation for observation in obs_result.scalars()}
        claims: list[Claim] = []
        for claim in candidate_claims:
            observation_ids = _claim_observation_ids(claim)
            if observation_ids and all(item in observations_by_id for item in observation_ids):
                claims.append(claim)

        if not claims:
            logger.warning("memo_no_scoped_claim_evidence", person_id=person_id)
            return {"error": "no_accepted_claim_evidence", "person_id": person_id}

        claim_ids = [str(claim.id) for claim in claims]
        observations = [
            observations_by_id[observation_id]
            for claim in claims
            for observation_id in (_claim_observation_ids(claim) or [])
        ]
        # Preserve first occurrence while keeping the input deterministic.
        observations = list({observation.id: observation for observation in observations}.values())
        evidence_text, obs_ids = build_evidence_text(observations, person)
        evidence_text = _claim_context(claims) + "\n\n" + evidence_text

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
            .where(Assessment.opportunity_id == opportunity.id)
            .order_by(Assessment.created_at.asc(), Assessment.id.asc())
        )
        assessments = list(assessment_result.scalars().all())
        assessment_ids = [str(assessment.id) for assessment in assessments]
        if assessments:
            scorecard_summary += "\n\nAssessments:\n" + "\n".join(
                f"- {a.axis}: {a.rating} (conf {a.confidence}) — {a.unknowns}"
                for a in assessments
            )
        else:
            scorecard_summary += "\n\nAssessments: unavailable for this opportunity."

        contradiction_result = await session.execute(
            select(Claim)
            .where(
                Claim.subject_id == person.id,
                Claim.opportunity_id == opportunity.id,
                Claim.status == "contradicted",
                Claim.supersession_id.is_(None),
            )
            .order_by(Claim.created_at.asc(), Claim.id.asc())
        )
        contradictions = list(contradiction_result.scalars().all())
        scorecard_summary += "\n\n" + _contradiction_context(contradictions)

        # Pin the thesis to the opportunity before generation. A later active
        # thesis change must not alter this memo's input package.
        if opportunity.thesis_version:
            thesis_result = await session.execute(
                select(InvestmentThesis).where(
                    InvestmentThesis.version == opportunity.thesis_version
                )
            )
        else:
            thesis_result = await session.execute(
                select(InvestmentThesis)
                .where(InvestmentThesis.is_active.is_(True))
                .order_by(InvestmentThesis.created_at.desc())
                .limit(1)
            )
        thesis = thesis_result.scalar_one_or_none()
        if thesis is None:
            logger.warning(
                "memo_no_pinned_thesis",
                person_id=person_id,
                opportunity_id=opportunity_id,
            )
            return {"error": "no_pinned_thesis", "person_id": person_id}
        if opportunity.thesis_version is None:
            opportunity.thesis_version = thesis.version
        thesis_summary = (
            f"{thesis.name} ({thesis.version}) — stages: {thesis.stages}, "
            f"sectors: {thesis.sectors}, regions: {thesis.regions}"
        )

        # Persist a pending run before calling the external model. If the
        # worker crashes, the pipeline retains an honest in-progress state.
        memo_record = InvestmentMemo(
            opportunity_id=opportunity.id,
            thesis_version=thesis.version,
            status="pending",
            claim_ids=claim_ids,
            assessment_ids=assessment_ids,
            sections={"sections": [], "generation_mode": "pending"},
            evidence_ids=sorted(obs_ids),
            model_version=settings.agent_model,
        )
        session.add(memo_record)
        await session.flush()
        proposal = DecisionProposal(
            opportunity_id=opportunity.id,
            memo_id=memo_record.id,
            **build_decision_proposal(
                assessments=assessments,
                claim_ids=claim_ids,
                thesis_version=thesis.version,
                memo_status="pending",
                memo_model_version=settings.agent_model,
                rubric_versions=("founder-agent-v1", "opportunity-axes-v1"),
            ),
        )
        session.add(proposal)
        await session.commit()

        # Generate memo
        semaphore = asyncio.Semaphore(settings.agent_concurrency)
        try:
            memo = await generate_memo(
                evidence_text=evidence_text,
                scorecard_summary=scorecard_summary,
                thesis_summary=thesis_summary,
                person_name=person.display_name or person.stable_id,
                api_key=settings.llm_api_key,
                model=settings.agent_model,
                semaphore=semaphore,
                allowed_claim_ids=claim_ids,
                allowed_evidence_ids=obs_ids,
            )
        except Exception as exc:
            memo_record.status = "failed"
            memo_record.sections = {
                "sections": [],
                "generation_mode": "failed",
                "error": "memo generation failed",
            }
            _apply_proposal_values(
                proposal,
                build_decision_proposal(
                    assessments=assessments,
                    claim_ids=claim_ids,
                    thesis_version=thesis.version,
                    memo_status="failed",
                    memo_model_version=settings.agent_model,
                    rubric_versions=("founder-agent-v1", "opportunity-axes-v1"),
                ),
            )
            await session.commit()
            logger.exception("memo_generation_failed", person_id=person_id, error=str(exc))
            return {"person_id": person_id, "status": "failed"}

        memo_record.status = memo.status
        memo_record.sections = {
            "sections": [s.model_dump() for s in memo.sections],
            "generation_mode": memo.generation_mode,
            "validation_errors": memo.validation_errors,
        }
        # Keep the durable evidence package limited to observations belonging
        # to the accepted claims. Citation validation is a separate contract.
        memo_record.evidence_ids = obs_ids
        memo_record.model_version = memo.model_version or settings.agent_model
        _apply_proposal_values(
            proposal,
            build_decision_proposal(
                assessments=assessments,
                claim_ids=claim_ids,
                thesis_version=thesis.version,
                memo_status=memo.status,
                memo_model_version=memo_record.model_version,
                rubric_versions=("founder-agent-v1", "opportunity-axes-v1"),
            ),
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
        "status": memo.status,
    }
