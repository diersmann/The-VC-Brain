"""Integration coverage for the canonical inbound pitch submission endpoint."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.routes import inbound
from app.db.models import Opportunity, Person, SourceSnapshot
from app.db.session import get_session
from app.main import app


class _FakeSession:
    def __init__(self, person: Person) -> None:
        self.person = person
        self.added: list[object] = []
        self.committed = False

    async def execute(self, _statement: object) -> SimpleNamespace:
        return SimpleNamespace(scalar_one_or_none=lambda: self.person)

    def add(self, instance: object) -> None:
        if isinstance(instance, SourceSnapshot) and instance.id is None:
            instance.id = uuid.uuid4()
        self.added.append(instance)

    async def commit(self) -> None:
        self.committed = True


class _FakeRedis:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict[str, object]]] = []

    async def enqueue_job(self, name: str, **kwargs: object) -> None:
        self.jobs.append((name, kwargs))


def test_submission_persists_uploaded_deck_and_returns_opportunity_id(monkeypatch) -> None:
    person = Person(
        id=uuid.uuid4(),
        stable_id="email:alice@example.com",
        display_name="Alice Example",
        email="alice@example.com",
        handles={"email": "alice@example.com"},
        consent_state="pending",
    )
    opportunity = Opportunity(
        id=uuid.uuid4(),
        company_name="Example AI",
        source_kind="inbound",
        lifecycle_state="received",
    )
    session = _FakeSession(person)
    redis = _FakeRedis()
    put_snapshot = AsyncMock(return_value=("hash-1", "snapshots/hash-1.pdf"))

    async def fake_opportunity(*_args, **_kwargs) -> Opportunity:
        return opportunity

    async def override_session():
        return session

    monkeypatch.setattr(inbound, "put_snapshot", put_snapshot)
    monkeypatch.setattr(inbound, "create_inbound_opportunity", fake_opportunity)
    monkeypatch.setattr(inbound, "_get_redis", AsyncMock(return_value=redis))
    app.dependency_overrides[get_session] = override_session

    try:
        response = TestClient(app).post(
            "/api/v1/inbound/pitch",
            data={
                "founder_name": "Alice Example",
                "founder_email": "alice@example.com",
                "company_name": "Example AI",
            },
            files={"file": ("pitch.pdf", b"%PDF-1.7 deck", "application/pdf")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["opportunity_id"] == str(opportunity.id)
    assert session.committed is True
    snapshot = next(item for item in session.added if isinstance(item, SourceSnapshot))
    assert snapshot.content_hash == "hash-1"
    assert snapshot.storage_path == "snapshots/hash-1.pdf"
    put_snapshot.assert_awaited_once()
    assert put_snapshot.await_args.kwargs["content"] == b"%PDF-1.7 deck"
    assert redis.jobs[0][0] == "process_inbound_pitch_job"
    assert redis.jobs[0][1]["opportunity_id"] == str(opportunity.id)
