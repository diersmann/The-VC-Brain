"""Deterministic, evidence-aware investment thesis alignment scoring."""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    InvestmentThesis,
    Observation,
    Opportunity,
    OpportunityFounder,
    Person,
    ScoreSnapshot,
)

CriterionStatus = Literal["matched", "failed", "unknown"]

DEFAULT_WEIGHTS = {"stage": 0.30, "sector": 0.40, "geography": 0.20, "check_size": 0.10}

_STAGE_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("series-c", ("series c", "series-c")),
    ("series-b", ("series b", "series-b")),
    ("series-a", ("series a", "series-a")),
    ("seed", ("seed round", "seed-stage", " seed ")),
    ("pre-seed", ("pre-seed", "preseed", "first round", "initial round", "angel round")),
]

_SECTOR_TERMS: dict[str, tuple[str, ...]] = {
    "ai": ("artificial intelligence", "machine learning", "generative ai", "llm", " ai "),
    "deep-tech": ("deep tech", "robotics", "quantum", "semiconductor", "infrastructure"),
    "b2b": (
        "b2b",
        "saas",
        "enterprise",
        "developer tool",
        "customer operations",
        "customer service",
        "product analytics",
        "recruiting platform",
        "business software",
    ),
    "climate": ("climate", "clean energy", "carbon", "sustainability"),
    "fintech": ("fintech", "payments", "banking", "insurance", "crypto"),
    "health": ("healthcare", "health tech", "biotech", "medical", "therapeutic"),
}

_REGION_TERMS: dict[str, tuple[str, ...]] = {
    "dach": ("germany", "berlin", "munich", "hamburg", "austria", "vienna", "switzerland"),
    "europe": (
        "europe",
        "germany",
        "berlin",
        "austria",
        "switzerland",
        "ireland",
        "dublin",
        "united kingdom",
        "london",
        "france",
        "paris",
        "netherlands",
        "amsterdam",
    ),
    "uk": ("united kingdom", " uk ", "london", "england", "scotland"),
    "us": ("united states", " usa ", " us ", "san francisco", "silicon valley", "new york"),
}


@dataclass(frozen=True)
class ThesisScore:
    score: float
    confidence: float
    hard_eligible: bool
    criteria: dict[str, dict[str, object]]
    matched: list[str]
    failed: list[str]
    unknown: list[str]
    evidence_ids: list[str]


def _bounded_text(values: list[str]) -> str:
    return f" {' '.join(values).lower()} "


def _observations_for(
    observations: list[Observation], predicates: set[str]
) -> list[Observation]:
    return [item for item in observations if item.predicate.lower() in predicates]


def _detect_stage(observations: list[Observation]) -> tuple[str | None, list[Observation]]:
    relevant = _observations_for(
        observations,
        {
            "pitch_deck_stage",
            "stage",
            "funding_stage",
            "inbound_summary",
            "research_founder_summary",
        },
    )
    text = _bounded_text([item.object_value for item in relevant])
    for stage, patterns in _STAGE_PATTERNS:
        if any(pattern in text for pattern in patterns):
            return stage, relevant
    return None, relevant


def _detect_sectors(observations: list[Observation]) -> tuple[list[str], list[Observation]]:
    relevant = _observations_for(
        observations,
        {
            "sector",
            "company",
            "bio",
            "inbound_summary",
            "research_market_summary",
            "research_idea_market_summary",
        },
    )
    text = _bounded_text([item.object_value for item in relevant])
    detected = [
        sector for sector, terms in _SECTOR_TERMS.items() if any(term in text for term in terms)
    ]
    return detected, relevant


def _detect_regions(observations: list[Observation]) -> tuple[list[str], list[Observation]]:
    relevant = _observations_for(observations, {"location", "city", "country", "headquarters"})
    text = _bounded_text([item.object_value for item in relevant])
    detected = [
        region for region, terms in _REGION_TERMS.items() if any(term in text for term in terms)
    ]
    return detected, relevant


def _detect_requested_check(
    observations: list[Observation],
) -> tuple[float | None, list[Observation]]:
    relevant = _observations_for(
        observations, {"target_check_k_eur", "requested_check_k_eur"}
    )
    for item in relevant:
        match = re.search(r"\d+(?:\.\d+)?", item.object_value.replace(",", ""))
        if match:
            return float(match.group()), relevant
    return None, relevant


def _criterion(
    *,
    status: CriterionStatus,
    expected: object,
    observed: object,
    explanation: str,
    evidence: list[Observation],
    hard: bool,
) -> dict[str, object]:
    return {
        "status": status,
        "expected": expected,
        "observed": observed,
        "explanation": explanation,
        "hard_constraint": hard,
        "evidence_ids": [str(item.id) for item in evidence],
    }


def score_thesis_alignment(
    thesis: InvestmentThesis, observations: list[Observation]
) -> ThesisScore:
    """Score thesis fit without treating missing evidence as a negative signal."""
    weights = {**DEFAULT_WEIGHTS, **(thesis.scoring_weights or {})}
    total_weight = sum(max(0.0, float(value)) for value in weights.values()) or 1.0
    weights = {key: max(0.0, float(value)) / total_weight for key, value in weights.items()}

    stage, stage_evidence = _detect_stage(observations)
    sectors, sector_evidence = _detect_sectors(observations)
    regions, region_evidence = _detect_regions(observations)
    requested_check, check_evidence = _detect_requested_check(observations)

    selected_stages = set(thesis.stages)
    selected_sectors = set(thesis.sectors)
    excluded_sectors = set(thesis.excluded_sectors)
    selected_regions = set(thesis.regions)

    if stage is None:
        stage_status: CriterionStatus = "unknown"
        stage_explanation = "Company stage is not supported by available evidence."
    elif stage in selected_stages:
        stage_status = "matched"
        stage_explanation = f"Observed {stage} is inside the active stage mandate."
    else:
        stage_status = "failed"
        stage_explanation = f"Observed {stage} is outside the active stage mandate."

    excluded_matches = sorted(set(sectors) & excluded_sectors)
    preferred_matches = sorted(set(sectors) & selected_sectors)
    if not sectors:
        sector_status: CriterionStatus = "unknown"
        sector_explanation = "Sector could not be classified from current evidence."
    elif excluded_matches:
        sector_status = "failed"
        sector_explanation = f"Detected excluded sector: {', '.join(excluded_matches)}."
    elif preferred_matches:
        sector_status = "matched"
        sector_explanation = f"Detected preferred sector: {', '.join(preferred_matches)}."
    else:
        sector_status = "failed"
        sector_explanation = "Detected sectors do not overlap the active thesis."

    region_matches = sorted(set(regions) & selected_regions)
    if "global" in selected_regions:
        geography_status: CriterionStatus = "matched"
        geography_explanation = "The thesis accepts companies globally."
    elif not regions:
        geography_status = "unknown"
        geography_explanation = "Geography is not supported by available evidence."
    elif region_matches:
        geography_status = "matched"
        geography_explanation = f"Detected eligible geography: {', '.join(region_matches)}."
    else:
        geography_status = "failed"
        geography_explanation = "Detected geography is outside the active thesis."

    check_range = [thesis.check_size_min_k_eur, thesis.check_size_max_k_eur]
    if requested_check is None:
        check_status: CriterionStatus = "unknown"
        check_explanation = "Requested investor check size has not been disclosed."
    elif (
        thesis.check_size_min_k_eur is not None
        and requested_check < thesis.check_size_min_k_eur
    ) or (
        thesis.check_size_max_k_eur is not None
        and requested_check > thesis.check_size_max_k_eur
    ):
        check_status = "failed"
        check_explanation = "Requested check is outside the configured ticket range."
    else:
        check_status = "matched"
        check_explanation = "Requested check is inside the configured ticket range."

    criteria = {
        "stage": _criterion(
            status=stage_status,
            expected=thesis.stages,
            observed=stage,
            explanation=stage_explanation,
            evidence=stage_evidence,
            hard=True,
        ),
        "sector": _criterion(
            status=sector_status,
            expected=thesis.sectors,
            observed=sectors,
            explanation=sector_explanation,
            evidence=sector_evidence,
            hard=bool(excluded_matches),
        ),
        "geography": _criterion(
            status=geography_status,
            expected=thesis.regions,
            observed=regions,
            explanation=geography_explanation,
            evidence=region_evidence,
            hard=False,
        ),
        "check_size": _criterion(
            status=check_status,
            expected=check_range,
            observed=requested_check,
            explanation=check_explanation,
            evidence=check_evidence,
            hard=False,
        ),
    }

    points = {"matched": 1.0, "failed": 0.0, "unknown": 0.5}
    score = sum(
        weights[key] * points[str(value["status"])] for key, value in criteria.items()
    )
    hard_eligible = stage_status != "failed" and not excluded_matches
    if not hard_eligible:
        score = min(score, 0.35)

    known_keys = [key for key, value in criteria.items() if value["status"] != "unknown"]
    known_weight = sum(weights[key] for key in known_keys)
    relevant_evidence = [
        item
        for items in (stage_evidence, sector_evidence, region_evidence, check_evidence)
        for item in items
    ]
    average_evidence_confidence = (
        sum(item.confidence for item in relevant_evidence) / len(relevant_evidence)
        if relevant_evidence
        else 0.0
    )
    confidence = max(0.15, known_weight * average_evidence_confidence)

    labels = {
        "stage": "Stage",
        "sector": "Sector",
        "geography": "Geography",
        "check_size": "Check size",
    }
    matched = [labels[key] for key, value in criteria.items() if value["status"] == "matched"]
    failed = [labels[key] for key, value in criteria.items() if value["status"] == "failed"]
    unknown = [labels[key] for key, value in criteria.items() if value["status"] == "unknown"]
    evidence_ids = list(dict.fromkeys(str(item.id) for item in relevant_evidence))

    return ThesisScore(
        score=round(score, 4),
        confidence=round(min(1.0, confidence), 4),
        hard_eligible=hard_eligible,
        criteria=criteria,
        matched=matched,
        failed=failed,
        unknown=unknown,
        evidence_ids=evidence_ids,
    )


async def score_all_candidates(session: AsyncSession, thesis: InvestmentThesis) -> int:
    """Append one thesis score snapshot per canonical candidate."""
    people_result = await session.execute(select(Person).where(Person.canonical.is_(True)))
    people = list(people_result.scalars().all())
    if not people:
        return 0

    person_ids = [person.id for person in people]
    observations_result = await session.execute(
        select(Observation)
        .where(Observation.subject_id.in_(person_ids))
        .order_by(Observation.observed_at.desc())
    )
    observations_by_person: dict[uuid.UUID, list[Observation]] = defaultdict(list)
    for observation in observations_result.scalars().all():
        if observation.subject_id is not None:
            observations_by_person[observation.subject_id].append(observation)

    opportunities_result = await session.execute(
        select(OpportunityFounder.person_id, Opportunity)
        .join(Opportunity, Opportunity.id == OpportunityFounder.opportunity_id)
        .where(OpportunityFounder.person_id.in_(person_ids))
        .order_by(Opportunity.created_at.desc())
    )
    latest_opportunity: dict[uuid.UUID, Opportunity] = {}
    for person_id, opportunity in opportunities_result.all():
        latest_opportunity.setdefault(person_id, opportunity)

    for person in people:
        result = score_thesis_alignment(thesis, observations_by_person.get(person.id, []))
        margin = round((1.0 - result.confidence) * 0.2, 4)
        session.add(
            ScoreSnapshot(
                subject_id=person.id,
                subject_type="person",
                rubric_version=f"thesis-match-v1:{thesis.version}",
                components={
                    "thesis_fit": result.score,
                    "thesis_confidence": result.confidence,
                    "thesis_version": thesis.version,
                    "hard_eligible": result.hard_eligible,
                    "criteria": result.criteria,
                    "matched": result.matched,
                    "failed": result.failed,
                    "unknown": result.unknown,
                },
                confidence_interval={
                    "thesis_fit": {
                        "low": round(max(0.0, result.score - margin), 4),
                        "high": round(min(1.0, result.score + margin), 4),
                    }
                },
                evidence_ids=result.evidence_ids,
            )
        )
        opportunity = latest_opportunity.get(person.id)
        if opportunity is not None:
            opportunity.thesis_version = thesis.version

    await session.flush()
    return len(people)
