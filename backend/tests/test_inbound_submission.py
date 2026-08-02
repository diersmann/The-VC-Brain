"""Integration coverage for the canonical inbound pitch submission endpoint."""

from __future__ import annotations

import io
import sys
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pypdf
import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from starlette.datastructures import Headers

from app.api.routes import inbound
from app.config import Settings
from app.db.models import Opportunity, Person, SourceSnapshot
from app.db.session import get_session
from app.main import app
from app.uploads import UploadRejected, quarantine_pitch_upload


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


def _pdf_bytes(*, pages: int = 1, password: str | None = None) -> bytes:
    writer = pypdf.PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    if password:
        writer.encrypt(password)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _upload(
    content: bytes,
    *,
    filename: str = "pitch.pdf",
    content_type: str = "application/pdf",
) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


@pytest.mark.asyncio
async def test_quarantine_rejects_oversized_upload() -> None:
    with pytest.raises(UploadRejected, match="exceeds"):
        await quarantine_pitch_upload(
            _upload(_pdf_bytes()), Settings(environment="test", upload_max_bytes=10)
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content", "filename", "content_type", "settings", "message"),
    [
        (
            b"%PDF-1.7\n%%EOF",
            "pitch.pdf",
            "application/pdf",
            Settings(environment="test"),
            "parsed safely",
        ),
        (
            _pdf_bytes() + b"PK\x03\x04",
            "pitch.pdf",
            "application/pdf",
            Settings(environment="test"),
            "trailing",
        ),
        (
            _pdf_bytes(password="secret"),
            "pitch.pdf",
            "application/pdf",
            Settings(environment="test"),
            "Encrypted",
        ),
        (
            _pdf_bytes(pages=2),
            "pitch.pdf",
            "application/pdf",
            Settings(environment="test", upload_max_pages=1),
            "page",
        ),
        (_pdf_bytes(), "pitch.pptx", "application/pdf", Settings(environment="test"), "Only PDF"),
        (_pdf_bytes(), "pitch.pdf", "text/html", Settings(environment="test"), "MIME"),
    ],
)
async def test_quarantine_rejects_unsafe_deck_variants(
    content: bytes,
    filename: str,
    content_type: str,
    settings: Settings,
    message: str,
) -> None:
    with pytest.raises(UploadRejected, match=message):
        await quarantine_pitch_upload(
            _upload(content, filename=filename, content_type=content_type), settings
        )


@pytest.mark.asyncio
async def test_quarantine_requires_scanner_outside_development() -> None:
    with pytest.raises(UploadRejected, match="scanner"):
        await quarantine_pitch_upload(
            _upload(_pdf_bytes()), Settings(environment="production")
        )


@pytest.mark.asyncio
async def test_quarantine_runs_configured_scanner() -> None:
    scanner = (
        f"{sys.executable} -c "
        "'import pathlib, sys; "
        "assert pathlib.Path(sys.argv[1]).read_bytes().startswith(b\"%PDF-\")'"
    )
    content = _pdf_bytes()
    result = await quarantine_pitch_upload(
        _upload(content), Settings(environment="production", upload_malware_scanner=scanner)
    )
    assert result == content


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
            files={"file": ("pitch.pdf", _pdf_bytes(), "application/pdf")},
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
    assert put_snapshot.await_args.kwargs["content"].startswith(b"%PDF-")
    assert redis.jobs[0][0] == "process_inbound_pitch_job"
    assert redis.jobs[0][1]["opportunity_id"] == str(opportunity.id)
