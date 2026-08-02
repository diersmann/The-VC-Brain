"""Import a small, idempotent set of official public pitch decks as inbound demos.

These records are explicitly labelled as public examples. They are not represented
as applications submitted by the founders or companies.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Observation,
    Opportunity,
    OpportunityFounder,
    Person,
    SourceSnapshot,
)
from app.db.session import _get_session_factory
from app.storage import close_client, put_snapshot

PUBLIC_INBOUND = [
    {
        "stable_id": "public-deck:intercom-eoghan-mccabe",
        "name": "Eoghan McCabe",
        "company": "Intercom",
        "role": "Co-founder & CEO",
        "location": "San Francisco, US / Dublin, Ireland",
        "website": "https://www.intercom.com",
        "deck_url": "https://www.intercom.com/blog/first-pitch-deck/",
        "deck_title": "Intercom's first pitch deck",
        "deck_stage": "First round · 2011",
        "sector": "AI customer service and customer communications",
        "summary": (
            "Eoghan McCabe co-founded Intercom with Des Traynor, David Barrett and Ciaran "
            "Lee. The official eight-slide deck framed a new way for online businesses to "
            "communicate with customers and sought an initial $600,000."
        ),
    },
    {
        "stable_id": "public-deck:front-mathilde-collin",
        "name": "Mathilde Collin",
        "company": "Front",
        "role": "Co-founder & Executive Chair",
        "location": "San Francisco, US",
        "website": "https://front.com",
        "deck_url": "https://front.com/blog/front-series-c-deck",
        "deck_title": "Front Series C deck",
        "deck_stage": "Series C · 2020",
        "sector": "Customer operations and collaborative inbox software",
        "summary": (
            "Mathilde Collin co-founded Front and publicly shared the deck used for its "
            "$59 million Series C. The materials explain the timing, financing process and "
            "company story behind the round."
        ),
    },
    {
        "stable_id": "public-deck:mixpanel-suhail-doshi",
        "name": "Suhail Doshi",
        "company": "Mixpanel",
        "role": "Co-founder",
        "location": "San Francisco, US",
        "website": "https://mixpanel.com",
        "deck_url": (
            "https://mixpanel.com/blog/"
            "open-sourcing-our-pitch-deck-that-helped-us-get-our-865m-valuation/"
        ),
        "deck_title": "Mixpanel's open-sourced pitch deck",
        "deck_stage": "Series C · 2014",
        "sector": "Product analytics",
        "summary": (
            "Suhail Doshi co-founded Mixpanel with Tim Trefren. Mixpanel's official public "
            "deck is the fundraising narrative the company says led to a $65 million round "
            "and an $865 million valuation in 2014."
        ),
    },
    {
        "stable_id": "public-deck:linkedin-reid-hoffman",
        "name": "Reid Hoffman",
        "company": "LinkedIn",
        "role": "Co-founder",
        "location": "Silicon Valley, US",
        "website": "https://www.linkedin.com",
        "deck_url": "https://www.reidhoffman.org/linkedin-pitch-to-greylock/",
        "deck_title": "LinkedIn's Series B pitch to Greylock",
        "deck_stage": "Series B · 2004",
        "sector": "Professional network and recruiting platform",
        "summary": (
            "Reid Hoffman co-founded LinkedIn and published the annotated deck used to "
            "pitch Greylock for its Series B in 2004. It explains the network thesis, "
            "revenue path, competition, risks and financing strategy slide by slide."
        ),
    },
]


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
        select(Observation).where(
            Observation.snapshot_id == snapshot_id,
            Observation.subject_id == person_id,
            Observation.predicate == predicate,
        ).order_by(Observation.created_at.desc()).limit(1)
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
                extractor_version=(
                    "public-inbound-v1"
                    if observation is None
                    else "public-inbound-v1-correction"
                ),
                confidence=confidence,
            )
        )


async def import_public_inbound() -> list[dict[str, str]]:
    now = datetime.now(UTC)
    imported: list[dict[str, str]] = []
    session_factory = _get_session_factory()

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=30,
        headers={"User-Agent": "The-VC-Brain public-deck importer/1.0"},
    ) as client, session_factory() as session:
        for record in PUBLIC_INBOUND:
            response = await client.get(record["deck_url"])
            response.raise_for_status()
            content_type = response.headers.get("content-type", "text/html").split(";", 1)[0]
            content_hash, storage_path = await put_snapshot(
                response.content,
                content_type,
                "public_pitch_deck",
            )

            snapshot_result = await session.execute(
                select(SourceSnapshot)
                .where(
                    SourceSnapshot.uri == record["deck_url"],
                    SourceSnapshot.source_type == "public_pitch_deck",
                )
                .order_by(SourceSnapshot.collected_at.desc())
                .limit(1)
            )
            snapshot = snapshot_result.scalar_one_or_none()
            if snapshot is None or snapshot.content_hash != content_hash:
                snapshot = SourceSnapshot(
                    uri=record["deck_url"],
                    source_type="public_pitch_deck",
                    content_hash=content_hash,
                    storage_path=storage_path,
                    license_metadata={
                        "source": "Official public pitch-deck page",
                        "usage": "Public demo reference; not a submitted fund application",
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
                        func.lower(Person.display_name) == record["name"].lower(),
                    )
                )
                .order_by(Person.created_at.asc())
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
            else:
                person.display_name = record["name"]

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
                    thesis_version="public-demo-v1",
                )
                session.add(opportunity)
                await session.flush()
                session.add(
                    OpportunityFounder(opportunity_id=opportunity.id, person_id=person.id)
                )

            observations = {
                "display_name": (record["name"], 1.0),
                "company": (record["company"], 1.0),
                "role": (record["role"], 0.95),
                "location": (record["location"], 0.8),
                "website": (record["website"], 1.0),
                "sector": (record["sector"], 0.9),
                "inbound_summary": (record["summary"], 0.95),
                "pitch_deck_url": (record["deck_url"], 1.0),
                "pitch_deck_title": (record["deck_title"], 1.0),
                "pitch_deck_stage": (record["deck_stage"], 0.95),
                "pitch_deck_format": ("Official public web deck", 1.0),
                "inbound_label": ("Public demo · not submitted", 1.0),
                "submission_note": (
                    "Imported from an official public source for product demonstration; "
                    "this is not a founder-submitted application.",
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

            imported.append(
                {
                    "person_id": str(person.id),
                    "name": record["name"],
                    "company": record["company"],
                    "deck_url": record["deck_url"],
                }
            )

        await session.commit()

    return imported


async def main() -> None:
    try:
        for item in await import_public_inbound():
            print(f"{item['person_id']}\t{item['name']}\t{item['company']}\t{item['deck_url']}")
    finally:
        await close_client()


if __name__ == "__main__":
    asyncio.run(main())
