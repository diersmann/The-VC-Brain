"""Seed a deterministic, synthetic local dataset for product demonstrations.

The records are deliberately fictional and clearly labelled.  No external network
request is made, and rerunning the command reuses the same people, opportunities,
snapshots, and observations.
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Assessment,
    Claim,
    DecisionEvent,
    InvestmentMemo,
    InvestmentThesis,
    Observation,
    Opportunity,
    OpportunityFounder,
    Person,
    ScoreSnapshot,
    SourceSnapshot,
)
from app.db.session import _get_session_factory
from app.storage import close_client, put_snapshot

DEMO_RECORDS = [
    {
        "stable_id": "demo:meridian-labs-ada-chen",
        "name": "Ada Chen",
        "company": "Meridian Labs",
        "role": "Co-founder & CEO",
        "location": "Berlin, Germany",
        "website": "https://demo.local/meridian-labs",
        "sector": "Developer tools and observability",
        "summary": (
            "Synthetic demo founder building a developer observability workspace for small"
            " engineering teams."
        ),
    },
    {
        "stable_id": "demo:northstar-health-mateo-ruiz",
        "name": "Mateo Ruiz",
        "company": "Northstar Health",
        "role": "Co-founder & CTO",
        "location": "Barcelona, Spain",
        "website": "https://demo.local/northstar-health",
        "sector": "Care coordination software",
        "summary": (
            "Synthetic demo founder building care coordination software for independent"
            " clinics and their patients."
        ),
    },
]

DEMO_WORKFLOW = {
    "demo:meridian-labs-ada-chen": {
        "lifecycle_state": "memo_ready",
        "scores": {
            "founder": 0.84,
            "market": 0.79,
            "idea_market": 0.76,
            "thesis_fit": 0.88,
            "evidence_confidence": 0.82,
            "momentum": 0.80,
            "composite": 0.83,
        },
        "prior_scores": {
            "founder": 0.78,
            "thesis_fit": 0.81,
            "evidence_confidence": 0.68,
            "momentum": 0.72,
            "composite": 0.77,
        },
        "assessments": [
            ("Founder", "Bullish", "Improving", 0.86, ["Validate repeat hiring outcomes"]),
            ("Market", "Bullish", "Stable", 0.78, ["Confirm bottom-up market size"]),
            (
                "Idea-Market",
                "Bullish",
                "Improving",
                0.80,
                ["Test expansion beyond observability teams"],
            ),
        ],
        "claims": [
            (
                "product_focus",
                "Developer observability workspace for small engineering teams",
                "supported",
                0.88,
            ),
            (
                "customer_signal",
                "Three design partners are testing the workflow",
                "supported",
                0.76,
            ),
            ("market_size", "The initial market estimate is €18m", "unverified", 0.42),
            (
                "market_size",
                "An older brief estimated the initial market at €4m",
                "contradicted",
                0.35,
            ),
        ],
        "memo": True,
    },
    "demo:northstar-health-mateo-ruiz": {
        "lifecycle_state": "investigating",
        "scores": {
            "founder": 0.71,
            "market": 0.58,
            "idea_market": 0.63,
            "thesis_fit": 0.64,
            "evidence_confidence": 0.55,
            "momentum": 0.61,
            "composite": 0.65,
        },
        "prior_scores": {
            "founder": 0.67,
            "thesis_fit": 0.59,
            "evidence_confidence": 0.44,
            "momentum": 0.55,
            "composite": 0.60,
        },
        "assessments": [
            ("Founder", "Bullish", "Stable", 0.72, ["Verify clinical implementation experience"]),
            ("Market", "Neutral", "Improving", 0.56, ["Reconcile provider adoption evidence"]),
            ("Idea-Market", "Neutral", "Stable", 0.60, ["Clarify reimbursement path"]),
        ],
        "claims": [
            (
                "product_focus",
                "Care coordination software for independent clinics",
                "supported",
                0.82,
            ),
            ("customer_signal", "Pilot clinic count is not disclosed", "unverified", 0.40),
            (
                "market_signal",
                "The source brief describes a fragmented provider market",
                "supported",
                0.68,
            ),
        ],
        "memo": False,
    },
}

DEMO_THESIS = {
    "version": "demo-v1",
    "name": "Synthetic Demo Thesis",
    "stages": ["pre-seed", "seed"],
    "sectors": ["ai", "deep-tech", "b2b", "health"],
    "regions": ["dach", "europe"],
}


def _source_content(record: dict[str, str]) -> bytes:
    """Return stable source bytes so the demo snapshot hash never changes."""
    return (
        "<!doctype html><html><body>"
        f"<h1>{record['company']} · synthetic demo brief</h1>"
        f"<p>Founder: {record['name']}</p>"
        f"<p>Role: {record['role']}</p>"
        f"<p>Sector: {record['sector']}</p>"
        f"<p>{record['summary']}</p>"
        "<p>This is fictional local demo data, not a submitted application.</p>"
        "</body></html>"
    ).encode()


async def _upsert_observation(
    session: AsyncSession,
    *,
    snapshot_id: uuid.UUID,
    person_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    predicate: str,
    value: str,
    confidence: float,
    observed_at: datetime,
) -> uuid.UUID:
    result = await session.execute(
        select(Observation)
        .where(
            Observation.snapshot_id == snapshot_id,
            Observation.subject_id == person_id,
            Observation.predicate == predicate,
        )
        .order_by(Observation.created_at.desc())
        .limit(1)
    )
    observation = result.scalar_one_or_none()
    if observation is None or (
        observation.object_value != value or observation.confidence != confidence
    ):
        observation = Observation(
            snapshot_id=snapshot_id,
            subject_id=person_id,
            opportunity_id=opportunity_id,
            predicate=predicate,
            object_value=value,
            observed_at=observed_at,
            extractor_version="demo-seed-v1",
            confidence=confidence,
        )
        session.add(observation)
        await session.flush()
    return observation.id


async def _upsert_score(
    session: AsyncSession,
    *,
    subject_id: uuid.UUID,
    subject_type: str,
    rubric_version: str,
    components: dict[str, object],
    evidence_ids: list[str],
) -> uuid.UUID:
    result = await session.execute(
        select(ScoreSnapshot)
        .where(
            ScoreSnapshot.subject_id == subject_id,
            ScoreSnapshot.subject_type == subject_type,
            ScoreSnapshot.rubric_version == rubric_version,
        )
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if snapshot is None:
        snapshot = ScoreSnapshot(
            subject_id=subject_id,
            subject_type=subject_type,
            rubric_version=rubric_version,
            components=components,
            evidence_ids=evidence_ids,
            provenance={"source": "synthetic-demo", "fixture_version": "demo-v1"},
        )
        session.add(snapshot)
    else:
        snapshot.components = components
        snapshot.evidence_ids = evidence_ids
    await session.flush()
    return snapshot.id


async def _upsert_claim(
    session: AsyncSession,
    *,
    person_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    observation_id: uuid.UUID,
    predicate: str,
    value: str,
    status: str,
    confidence: float,
    now: datetime,
) -> uuid.UUID:
    result = await session.execute(
        select(Claim)
        .where(
            Claim.opportunity_id == opportunity_id,
            Claim.predicate == predicate,
            Claim.object_value == value,
        )
        .limit(1)
    )
    claim = result.scalar_one_or_none()
    if claim is None:
        claim = Claim(
            observation_ids=[str(observation_id)],
            subject_id=person_id,
            opportunity_id=opportunity_id,
            predicate=predicate,
            object_value=value,
            status=status,
            confidence=confidence,
            trust_version="demo-v1",
            trust_score=confidence,
            trust_interval={"low": max(0.0, confidence - 0.1), "high": min(1.0, confidence + 0.1)},
            trust_explanation="Synthetic demo claim with explicit fixture provenance.",
            valid_time_start=now,
        )
        session.add(claim)
    else:
        claim.status = status
        claim.confidence = confidence
        claim.trust_score = confidence
    await session.flush()
    return claim.id


async def _upsert_assessment(
    session: AsyncSession,
    *,
    opportunity_id: uuid.UUID,
    axis: str,
    rating: str,
    trend: str,
    confidence: float,
    claim_ids: list[str],
    now: datetime,
) -> uuid.UUID:
    result = await session.execute(
        select(Assessment)
        .where(Assessment.opportunity_id == opportunity_id, Assessment.axis == axis)
        .limit(1)
    )
    assessment = result.scalar_one_or_none()
    unknowns = ["Synthetic demo assessment; validate against primary evidence."]
    if assessment is None:
        assessment = Assessment(
            opportunity_id=opportunity_id,
            axis=axis,
            rating=rating,
            trend=trend,
            confidence=confidence,
            evidence_ids=claim_ids,
            counter_evidence_ids=[],
            unknowns=unknowns,
        )
        session.add(assessment)
    else:
        assessment.rating = rating
        assessment.trend = trend
        assessment.confidence = confidence
        assessment.evidence_ids = claim_ids
        assessment.unknowns = unknowns
    await session.flush()
    return assessment.id


async def _upsert_memo(
    session: AsyncSession,
    *,
    opportunity_id: uuid.UUID,
    claim_ids: list[str],
    assessment_ids: list[str],
    evidence_ids: list[str],
) -> None:
    result = await session.execute(
        select(InvestmentMemo).where(InvestmentMemo.opportunity_id == opportunity_id).limit(1)
    )
    memo = result.scalar_one_or_none()
    sections = [
        {
            "title": "Company snapshot",
            "text": "Synthetic demo company with evidence-backed product and founder context.",
            "claim_ids": claim_ids[:1],
            "evidence_ids": evidence_ids[:1],
        },
        {
            "title": "Investment hypotheses",
            "text": (
                "The thesis fit is promising, subject to the recorded unknowns and "
                "contradiction review."
            ),
            "claim_ids": claim_ids,
            "evidence_ids": evidence_ids,
        },
        {
            "title": "SWOT",
            "text": "Strength: clear product focus. Risk: market sizing requires reconciliation.",
            "claim_ids": claim_ids,
            "evidence_ids": evidence_ids,
        },
        {
            "title": "Problem and product",
            "text": "The product brief describes a focused workflow for the target customer group.",
            "claim_ids": claim_ids[:1],
            "evidence_ids": evidence_ids[:1],
        },
        {
            "title": "Traction and KPIs",
            "text": (
                "Available traction is limited to the synthetic evidence fixture and "
                "is not a verified KPI claim."
            ),
            "claim_ids": claim_ids[1:2],
            "evidence_ids": evidence_ids[1:2],
        },
    ]
    if memo is None:
        session.add(
            InvestmentMemo(
                opportunity_id=opportunity_id,
                thesis_version="demo-v1",
                status="succeeded",
                claim_ids=claim_ids,
                assessment_ids=assessment_ids,
            sections={"sections": sections, "generation_mode": "template_fallback"},
                evidence_ids=evidence_ids,
                model_version="synthetic-demo-v1",
            )
        )
    else:
        memo.status = "succeeded"
        memo.claim_ids = claim_ids
        memo.assessment_ids = assessment_ids
        memo.sections = {"sections": sections, "generation_mode": "template_fallback"}
        memo.evidence_ids = evidence_ids
    await session.flush()


async def _upsert_decision_event(
    session: AsyncSession,
    *,
    opportunity_id: uuid.UUID,
    new_state: str,
    idempotency_key: str,
) -> None:
    result = await session.execute(
        select(DecisionEvent).where(DecisionEvent.idempotency_key == idempotency_key).limit(1)
    )
    if result.scalar_one_or_none() is None:
        session.add(
            DecisionEvent(
                opportunity_id=opportunity_id,
                prior_state="received",
                new_state=new_state,
                actor="synthetic-demo",
                idempotency_key=idempotency_key,
                reason="Deterministic local demo workflow fixture.",
            )
        )
        await session.flush()


async def _seed_workflow(
    session: AsyncSession,
    *,
    record: dict[str, str],
    person: Person,
    opportunity: Opportunity,
    observation_ids: list[uuid.UUID],
    now: datetime,
) -> None:
    workflow = DEMO_WORKFLOW[record["stable_id"]]
    person_scores = workflow["scores"]
    prior_scores = workflow["prior_scores"]
    evidence_ids = [str(item) for item in observation_ids]
    await _upsert_score(
        session,
        subject_id=person.id,
        subject_type="person",
        rubric_version="demo-founder-history-v1",
        components=prior_scores,
        evidence_ids=evidence_ids[:3],
    )
    await _upsert_score(
        session,
        subject_id=person.id,
        subject_type="person",
        rubric_version="demo-founder-v1",
        components=person_scores,
        evidence_ids=evidence_ids,
    )
    thesis_components = {
        "thesis_fit": person_scores["thesis_fit"],
        "thesis_confidence": person_scores["evidence_confidence"],
        "thesis_version": "demo-v1",
        "hard_eligible": person_scores["thesis_fit"] >= 0.75,
        "matched": ["Stage and sector overlap"],
        "failed": [],
        "unknown": ["Validate source depth"],
    }
    await _upsert_score(
        session,
        subject_id=person.id,
        subject_type="person",
        rubric_version="thesis-match-demo-v1",
        components=thesis_components,
        evidence_ids=evidence_ids,
    )
    axis_scores = {key: person_scores[key] for key in ("market", "idea_market")}
    axis_scores["evidence_confidence"] = person_scores["evidence_confidence"]
    await _upsert_score(
        session,
        subject_id=opportunity.id,
        subject_type="opportunity",
        rubric_version="opportunity-axes-v1",
        components=axis_scores,
        evidence_ids=evidence_ids,
    )

    claim_ids: list[str] = []
    for index, (predicate, value, status, confidence) in enumerate(workflow["claims"]):
        claim_ids.append(
            await _upsert_claim(
                session,
                person_id=person.id,
                opportunity_id=opportunity.id,
                observation_id=observation_ids[index % len(observation_ids)],
                predicate=predicate,
                value=value,
                status=status,
                confidence=confidence,
                now=now,
            )
        )
    assessment_ids: list[str] = []
    for axis, rating, trend, confidence, _unknowns in workflow["assessments"]:
        assessment_ids.append(
            await _upsert_assessment(
                session,
                opportunity_id=opportunity.id,
                axis=axis,
                rating=rating,
                trend=trend,
                confidence=confidence,
                claim_ids=[str(item) for item in claim_ids[:2]],
                now=now,
            )
        )
    if workflow["memo"]:
        await _upsert_memo(
            session,
            opportunity_id=opportunity.id,
            claim_ids=[str(item) for item in claim_ids],
            assessment_ids=[str(item) for item in assessment_ids],
            evidence_ids=evidence_ids,
        )
    opportunity.lifecycle_state = workflow["lifecycle_state"]
    await _upsert_decision_event(
        session,
        opportunity_id=opportunity.id,
        new_state=workflow["lifecycle_state"],
        idempotency_key=f"demo-seed:{record['stable_id']}:state",
    )


async def seed_demo() -> list[dict[str, str]]:
    now = datetime.now(UTC)
    seeded: list[dict[str, str]] = []
    session_factory = _get_session_factory()

    async with session_factory() as session:
        active_thesis_result = await session.execute(
            select(InvestmentThesis).where(InvestmentThesis.is_active.is_(True)).limit(1)
        )
        active_thesis = active_thesis_result.scalar_one_or_none()
        thesis_result = await session.execute(
            select(InvestmentThesis)
            .where(InvestmentThesis.version == DEMO_THESIS["version"])
            .limit(1)
        )
        thesis = thesis_result.scalar_one_or_none()
        if thesis is None:
            thesis = InvestmentThesis(
                version=DEMO_THESIS["version"],
                name=DEMO_THESIS["name"],
                is_active=active_thesis is None,
                stages=DEMO_THESIS["stages"],
                sectors=DEMO_THESIS["sectors"],
                excluded_sectors=[],
                regions=DEMO_THESIS["regions"],
                check_size_min_k_eur=250,
                check_size_max_k_eur=500,
                ownership_target_pct=10,
                risk_appetite="balanced",
                scoring_weights={
                    "stage": 0.30,
                    "sector": 0.40,
                    "geography": 0.20,
                    "check_size": 0.10,
                },
                discovery_queries=["synthetic demo founder"],
                source_freshness_days={"demo_seed": 3650},
            )
            session.add(thesis)
            await session.flush()
        for record in DEMO_RECORDS:
            source_uri = f"https://demo.local/{record['stable_id'].removeprefix('demo:')}"
            content = _source_content(record)
            content_hash = hashlib.sha256(content).hexdigest()
            snapshot_result = await session.execute(
                select(SourceSnapshot)
                .where(
                    SourceSnapshot.uri == source_uri,
                    SourceSnapshot.source_type == "demo_seed",
                )
                .order_by(SourceSnapshot.collected_at.desc())
                .limit(1)
            )
            snapshot = snapshot_result.scalar_one_or_none()
            if snapshot is None or snapshot.content_hash != content_hash:
                stored_hash, storage_path = await put_snapshot(content, "text/html", "demo_seed")
                snapshot = SourceSnapshot(
                    uri=source_uri,
                    source_type="demo_seed",
                    content_hash=stored_hash,
                    storage_path=storage_path,
                    license_metadata={
                        "source": "Synthetic local fixture",
                        "usage": "Development and product demonstration only",
                    },
                    collected_at=now,
                )
                session.add(snapshot)
                await session.flush()

            person_result = await session.execute(
                select(Person)
                .where(
                    or_(
                        Person.stable_id == record["stable_id"],
                        Person.display_name == record["name"],
                    )
                )
                .limit(1)
            )
            person = person_result.scalar_one_or_none()
            if person is None:
                person = Person(
                    stable_id=record["stable_id"],
                    display_name=record["name"],
                    consent_state="pending",
                    canonical=True,
                )
                session.add(person)
                await session.flush()

            opportunity_result = await session.execute(
                select(Opportunity)
                .join(OpportunityFounder, OpportunityFounder.opportunity_id == Opportunity.id)
                .where(
                    OpportunityFounder.person_id == person.id,
                    Opportunity.source_kind == "inbound",
                    Opportunity.company_name == record["company"],
                )
                .limit(1)
            )
            opportunity = opportunity_result.scalar_one_or_none()
            if opportunity is None:
                opportunity = Opportunity(
                    company_name=record["company"],
                    source_kind="inbound",
                    lifecycle_state="received",
                    thesis_version="demo-v1",
                )
                session.add(opportunity)
                await session.flush()
                session.add(OpportunityFounder(opportunity_id=opportunity.id, person_id=person.id))

            observations = {
                "display_name": (record["name"], 1.0),
                "company": (record["company"], 1.0),
                "role": (record["role"], 0.95),
                "location": (record["location"], 0.8),
                "website": (record["website"], 1.0),
                "sector": (record["sector"], 0.9),
                "inbound_summary": (record["summary"], 0.95),
                "pitch_deck_url": (source_uri, 1.0),
                "pitch_deck_title": (f"{record['company']} synthetic demo brief", 1.0),
                "inbound_label": ("Synthetic demo · not submitted", 1.0),
                "submission_note": (
                    "Fictional local fixture for product demonstration; this is not a"
                    " founder-submitted application.",
                    1.0,
                ),
            }
            observation_ids: list[uuid.UUID] = []
            for predicate, (value, confidence) in observations.items():
                observation_ids.append(
                    await _upsert_observation(
                        session,
                        snapshot_id=snapshot.id,
                        person_id=person.id,
                        opportunity_id=opportunity.id,
                        predicate=predicate,
                        value=value,
                        confidence=confidence,
                        observed_at=now,
                    )
                )

            await _seed_workflow(
                session,
                record=record,
                person=person,
                opportunity=opportunity,
                observation_ids=observation_ids,
                now=now,
            )

            seeded.append(
                {"person_id": str(person.id), "name": record["name"], "company": record["company"]}
            )

        await session.commit()

    return seeded


async def main() -> None:
    try:
        for item in await seed_demo():
            print(f"{item['person_id']}\t{item['name']}\t{item['company']}")
    finally:
        await close_client()


if __name__ == "__main__":
    asyncio.run(main())
