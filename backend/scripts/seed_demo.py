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

from app.db.models import Observation, Opportunity, OpportunityFounder, Person, SourceSnapshot
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
) -> None:
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
        session.add(
            Observation(
                snapshot_id=snapshot_id,
                subject_id=person_id,
                opportunity_id=opportunity_id,
                predicate=predicate,
                object_value=value,
                observed_at=observed_at,
                extractor_version="demo-seed-v1",
                confidence=confidence,
            )
        )


async def seed_demo() -> list[dict[str, str]]:
    now = datetime.now(UTC)
    seeded: list[dict[str, str]] = []
    session_factory = _get_session_factory()

    async with session_factory() as session:
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
            for predicate, (value, confidence) in observations.items():
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
