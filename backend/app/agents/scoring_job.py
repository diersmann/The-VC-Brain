"""Arq job for multi-agent candidate scoring."""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from sqlalchemy import select

from app.agents.scoring import build_evidence_text, score_candidate
from app.artifact_provenance import build_artifact_metadata, fingerprint_payload
from app.collectors.jobs import _session_ctx
from app.db.models import (
    Observation,
    Person,
    ScoreSnapshot,
    SourceSnapshot,
)
from app.job_ledger import start_job, update_job
from app.privacy import external_ai_use_decision

logger = structlog.get_logger(__name__)

async def score_candidate_job(
    ctx: dict[str, Any], person_id: str, job_id: str | None = None
) -> dict[str, Any]:
    """Run the multi-agent scoring committee for one candidate.

    Builds the evidence package from all observations, runs the 3 specialist
    agents + critic + aggregator, writes Assessments and a ScoreSnapshot.
    """
    from app.config import get_settings

    settings = ctx.get("settings") or get_settings()
    logger.info("score_candidate_job_started", person_id=person_id)

    async with _session_ctx(ctx) as session:
        job_attempt = 1
        if job_id:
            started_job = await start_job(session, job_id, phase="scoring")
            if started_job is not None:
                if started_job.status in {"succeeded", "cancelled"}:
                    return {
                        "person_id": person_id,
                        "status": "already_terminal",
                        "job_id": str(started_job.id),
                    }
                job_attempt = started_job.attempt
            await session.commit()

        async def finish_error(error: str) -> dict[str, Any]:
            if job_id:
                await update_job(
                    session,
                    job_id,
                    status="failed",
                    phase="scoring",
                    attempt=job_attempt,
                    last_error=error,
                    result={"error": error},
                )
                await session.commit()
            return {"error": error}

        try:
            parsed_person_id = uuid.UUID(person_id)
        except ValueError:
            return await finish_error("invalid_person_id")
        person = await session.get(Person, parsed_person_id)
        if person is None:
            logger.error("score_candidate_person_not_found", person_id=person_id)
            return await finish_error("person_not_found")

        if not person.canonical:
            logger.warning("score_candidate_not_canonical", person_id=person_id)
            return await finish_error("person_not_canonical")

        # Fetch all observations for the person
        observations_result = await session.execute(
            select(Observation)
            .join(SourceSnapshot, SourceSnapshot.id == Observation.snapshot_id)
            .where(Observation.subject_id == person.id)
            .where(SourceSnapshot.source_use_policy["model_use"].as_string() == "allowed")
            .order_by(Observation.observed_at.desc())
            .limit(500)
        )
        observations: list[Observation] = list(observations_result.scalars().all())

        if not observations:
            logger.warning("score_candidate_no_observations", person_id=person_id)
            return await finish_error("no_observations")

        ai_policy = external_ai_use_decision(person, "scoring")
        if settings.llm_api_key and not ai_policy.allowed:
            logger.warning(
                "score_candidate_external_ai_blocked",
                person_id=person_id,
                reason=ai_policy.reason,
            )
            error_result = {
                "error": "external_ai_blocked",
                "purpose": ai_policy.purpose,
                "reason": ai_policy.reason,
            }
            if job_id:
                await update_job(
                    session,
                    job_id,
                    status="failed",
                    phase="scoring",
                    attempt=job_attempt,
                    last_error=ai_policy.reason,
                    result=error_result,
                )
                await session.commit()
            return error_result

        # Build evidence package
        evidence_text, obs_ids = build_evidence_text(observations, person)
        run_id = uuid.uuid4()
        input_fingerprint = fingerprint_payload(
            {"observation_ids": obs_ids, "model": settings.agent_model}
        )
        scoring_started = time.perf_counter()

        # Run the scoring committee
        try:
            scorecard, _metadata = await score_candidate(
                evidence_text=evidence_text,
                api_key=settings.llm_api_key,
                model=settings.agent_model,
                concurrency=settings.agent_concurrency,
            )
        except Exception as exc:
            if job_id:
                await update_job(
                    session,
                    job_id,
                    status="failed",
                    phase="scoring",
                    attempt=job_attempt,
                    last_error=str(exc),
                    result={"error": "scoring_failed"},
                )
                await session.commit()
            raise

        # Specialist dimensions remain inputs to the persistent person-scoped
        # Founder Score. Opportunity assessments are written only by the
        # canonical Founder/Market/Idea-Market research job.
        score_components: dict[str, object] = {
            "founder": scorecard.composite / 100.0,  # 0-1 scale for candidates API
            "execution": scorecard.execution,
            "technical": scorecard.technical,
            "commercial": scorecard.commercial,
            "evidence_confidence": scorecard.confidence,
            "hard_eligible": scorecard.hard_eligible,
            "validator_status": scorecard.validator_status,
            "validation_errors": scorecard.validation_errors,
            "critique": [i.model_dump() for i in scorecard.critique],
            "agents": {dim: a.model_dump() for dim, a in scorecard.agents.items()},
        }
        artifact_metadata = build_artifact_metadata(
            run_id=run_id,
            artifact_type="score_snapshot",
            code_version="scoring-job-v2",
            input_fingerprint=input_fingerprint,
            rubric_versions=("founder-agent-v1",),
            prompt_version="scoring-prompts-v1",
            model_version=settings.agent_model,
            parameters={"concurrency": settings.agent_concurrency},
            latency_ms=round((time.perf_counter() - scoring_started) * 1000),
            validator_status=scorecard.validator_status,
            validator_errors=scorecard.validation_errors,
            compatibility={"reader": "score-snapshot-v1"},
        )

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
                artifact_metadata=artifact_metadata,
            )
        )

        result_payload = {
            "person_id": person_id,
            "composite": scorecard.composite,
            "confidence": scorecard.confidence,
            "hard_eligible": scorecard.hard_eligible,
            "model": settings.agent_model,
        }
        if job_id:
            await update_job(
                session,
                job_id,
                status="succeeded",
                phase="complete",
                attempt=job_attempt,
                clear_error=True,
                result=result_payload,
            )
        await session.commit()

    logger.info(
        "score_candidate_job_completed",
        person_id=person_id,
        composite=scorecard.composite,
        confidence=scorecard.confidence,
        model=settings.agent_model,
    )

    return result_payload
