"""Provider-free durable ledger coverage for inbound PDF parsing."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents import inbound_job
from app.db.models import JobRun, SourceSnapshot


def _session_for(job: JobRun, snapshot: SourceSnapshot | None) -> AsyncMock:
    session = AsyncMock()
    session.add_all = MagicMock()

    async def get(model: object, _identifier: object) -> object | None:
        if model is JobRun:
            return job
        if model is SourceSnapshot:
            return snapshot
        return None

    session.get.side_effect = get
    return session


def _patch_session(monkeypatch: pytest.MonkeyPatch, session: AsyncMock) -> None:
    @asynccontextmanager
    async def context(_ctx: dict[str, object]):
        yield session

    monkeypatch.setattr(inbound_job, "_session_ctx", context)


def _settings() -> SimpleNamespace:
    return SimpleNamespace(upload_max_pages=20, upload_max_text_chars=50_000)


def _snapshot() -> SourceSnapshot:
    return SourceSnapshot(
        id=uuid.uuid4(),
        uri="inbound://pitch.pdf",
        source_type="inbound_deck",
        content_hash="hash",
        storage_path="inbound/hash",
    )


def _args(job: JobRun | None = None) -> tuple[dict[str, object], str, str, str, str, str]:
    person_id = str(uuid.uuid4())
    snapshot_id = str(uuid.uuid4())
    opportunity_id = str(uuid.uuid4())
    job_id = str(job.id) if job else str(uuid.uuid4())
    return (
        {"session_factory": object(), "settings": _settings()},
        person_id,
        snapshot_id,
        opportunity_id,
        "Example AI",
        job_id,
    )


@pytest.mark.asyncio
async def test_inbound_parser_commits_running_before_extraction_and_final_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="process_inbound_pitch", attempt=0)
    snapshot = _snapshot()
    session = _session_for(job, snapshot)
    _patch_session(monkeypatch, session)
    events: list[str] = []

    async def get_pdf(_path: str) -> bytes:
        events.append("storage")
        assert session.commit.await_count >= 1
        return b"pdf"

    monkeypatch.setattr(inbound_job, "get_snapshot", get_pdf)
    monkeypatch.setattr(
        inbound_job,
        "extract_pdf_pages",
        lambda *_args, **_kwargs: [("deck text", {"kind": "pdf", "page": 1})],
    )
    monkeypatch.setattr(
        inbound_job,
        "process_candidate_job",
        AsyncMock(return_value={"status": "ok"}),
    )

    ctx, person_id, _snapshot_id, opportunity_id, company_name, job_id = _args(job)
    result = await inbound_job.process_inbound_pitch_job(
        ctx,
        person_id,
        str(snapshot.id),
        opportunity_id,
        company_name,
        job_id=job_id,
    )

    assert events == ["storage"]
    assert job.status == "succeeded"
    assert job.phase == "complete"
    assert job.attempt == 1
    assert job.result is not None
    assert job.result["observations_created"] == 2
    assert result["processing"] == {"status": "ok"}
    assert session.commit.await_count == 3


@pytest.mark.asyncio
async def test_inbound_parser_missing_snapshot_is_permanent_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="process_inbound_pitch", attempt=0)
    session = _session_for(job, None)
    _patch_session(monkeypatch, session)
    ctx, person_id, snapshot_id, opportunity_id, company_name, job_id = _args(job)

    result = await inbound_job.process_inbound_pitch_job(
        ctx, person_id, snapshot_id, opportunity_id, company_name, job_id=job_id
    )

    assert result["error"] == "snapshot_not_found"
    assert job.status == "failed"
    assert job.result == result
    assert result["failure_kind"] == "permanent"
    assert result["retryable"] is False


@pytest.mark.asyncio
async def test_inbound_parser_rejected_pdf_is_terminal_without_exception_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="process_inbound_pitch", attempt=0)
    snapshot = _snapshot()
    session = _session_for(job, snapshot)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(inbound_job, "get_snapshot", AsyncMock(return_value=b"pdf"))
    monkeypatch.setattr(
        inbound_job,
        "extract_pdf_pages",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            inbound_job.UploadRejected("founder secret")
        ),
    )
    ctx, person_id, _snapshot_id, opportunity_id, company_name, job_id = _args(job)

    result = await inbound_job.process_inbound_pitch_job(
        ctx, person_id, str(snapshot.id), opportunity_id, company_name, job_id=job_id
    )

    assert result["error"] == "pdf_rejected"
    assert result["failure_kind"] == "permanent"
    assert "founder secret" not in str(job.result)
    assert job.status == "failed"


@pytest.mark.asyncio
async def test_inbound_parser_unexpected_extraction_failure_is_classified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="process_inbound_pitch", attempt=0)
    snapshot = _snapshot()
    session = _session_for(job, snapshot)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(inbound_job, "get_snapshot", AsyncMock(return_value=b"pdf"))
    monkeypatch.setattr(
        inbound_job,
        "extract_pdf_pages",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("secret timeout")),
    )
    ctx, person_id, _snapshot_id, opportunity_id, company_name, job_id = _args(job)

    with pytest.raises(TimeoutError, match="secret timeout"):
        await inbound_job.process_inbound_pitch_job(
            ctx, person_id, str(snapshot.id), opportunity_id, company_name, job_id=job_id
        )

    assert job.status == "failed"
    assert job.result is not None
    assert job.result["error"] == "pdf_extraction_failed"
    assert job.result["failure_kind"] == "transient"
    assert job.result["retryable"] is True
    assert "secret timeout" not in str(job.result)
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_inbound_parser_terminal_duplicate_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    job = JobRun(
        id=uuid.uuid4(),
        job_type="process_inbound_pitch",
        status="succeeded",
        phase="complete",
        attempt=2,
        result={"status": "success", "observations_created": 2},
    )
    snapshot = _snapshot()
    session = _session_for(job, snapshot)
    _patch_session(monkeypatch, session)
    extractor = AsyncMock()
    monkeypatch.setattr(inbound_job, "get_snapshot", extractor)
    ctx, person_id, _snapshot_id, opportunity_id, company_name, job_id = _args(job)

    result = await inbound_job.process_inbound_pitch_job(
        ctx, person_id, str(snapshot.id), opportunity_id, company_name, job_id=job_id
    )

    assert result == job.result
    extractor.assert_not_awaited()


@pytest.mark.asyncio
async def test_inbound_parser_failed_job_retries_with_incremented_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="process_inbound_pitch", status="failed", attempt=2)
    snapshot = _snapshot()
    session = _session_for(job, snapshot)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(inbound_job, "get_snapshot", AsyncMock(return_value=b"pdf"))
    monkeypatch.setattr(
        inbound_job,
        "extract_pdf_pages",
        lambda *_args, **_kwargs: [("deck text", {"kind": "pdf", "page": 1})],
    )
    monkeypatch.setattr(inbound_job, "process_candidate_job", AsyncMock(return_value={}))
    ctx, person_id, _snapshot_id, opportunity_id, company_name, job_id = _args(job)

    await inbound_job.process_inbound_pitch_job(
        ctx, person_id, str(snapshot.id), opportunity_id, company_name, job_id=job_id
    )

    assert job.status == "succeeded"
    assert job.attempt == 3


@pytest.mark.asyncio
async def test_inbound_parser_downstream_failure_keeps_job_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="process_inbound_pitch", attempt=0)
    snapshot = _snapshot()
    session = _session_for(job, snapshot)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(inbound_job, "get_snapshot", AsyncMock(return_value=b"pdf"))
    monkeypatch.setattr(
        inbound_job,
        "extract_pdf_pages",
        lambda *_args, **_kwargs: [("deck text", {"kind": "pdf", "page": 1})],
    )
    monkeypatch.setattr(
        inbound_job,
        "process_candidate_job",
        AsyncMock(side_effect=TimeoutError("pipeline timed out")),
    )
    ctx, person_id, _snapshot_id, opportunity_id, company_name, job_id = _args(job)

    with pytest.raises(TimeoutError, match="pipeline timed out"):
        await inbound_job.process_inbound_pitch_job(
            ctx, person_id, str(snapshot.id), opportunity_id, company_name, job_id=job_id
        )

    assert job.status == "failed"
    assert job.phase == "processing"
    assert job.result is not None
    assert job.result["error"] == "processing_failed"
    assert job.result["failure_kind"] == "transient"
    assert job.result["retryable"] is True
    assert "pipeline timed out" not in str(job.result)


@pytest.mark.asyncio
async def test_inbound_parser_retry_reuses_observations_after_downstream_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="process_inbound_pitch", attempt=0)
    snapshot = _snapshot()
    session = _session_for(job, snapshot)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(inbound_job, "get_snapshot", AsyncMock(return_value=b"pdf"))
    monkeypatch.setattr(
        inbound_job,
        "extract_pdf_pages",
        lambda *_args, **_kwargs: [("deck text", {"kind": "pdf", "page": 1})],
    )
    process = AsyncMock(side_effect=[TimeoutError("pipeline timed out"), {"status": "ok"}])
    monkeypatch.setattr(inbound_job, "process_candidate_job", process)
    ctx, person_id, _snapshot_id, opportunity_id, company_name, job_id = _args(job)

    with pytest.raises(TimeoutError):
        await inbound_job.process_inbound_pitch_job(
            ctx, person_id, str(snapshot.id), opportunity_id, company_name, job_id=job_id
        )

    first_observations = list(session.add_all.call_args.args[0])
    session.execute.side_effect = lambda _statement: SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: first_observations)
    )

    result = await inbound_job.process_inbound_pitch_job(
        ctx, person_id, str(snapshot.id), opportunity_id, company_name, job_id=job_id
    )

    assert result["processing"] == {"status": "ok"}
    assert job.status == "succeeded"
    assert job.attempt == 2
    assert session.add_all.call_count == 2
    assert session.add_all.call_args.args[0] == []


@pytest.mark.asyncio
async def test_inbound_parser_downstream_error_result_is_terminalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="process_inbound_pitch", attempt=0)
    snapshot = _snapshot()
    session = _session_for(job, snapshot)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(inbound_job, "get_snapshot", AsyncMock(return_value=b"pdf"))
    monkeypatch.setattr(
        inbound_job,
        "extract_pdf_pages",
        lambda *_args, **_kwargs: [("deck text", {"kind": "pdf", "page": 1})],
    )
    monkeypatch.setattr(
        inbound_job,
        "process_candidate_job",
        AsyncMock(
            return_value={
                "status": "failed",
                "error": "pipeline_unavailable",
                "failure_kind": "transient",
                "retryable": True,
            }
        ),
    )
    ctx, person_id, _snapshot_id, opportunity_id, company_name, job_id = _args(job)

    result = await inbound_job.process_inbound_pitch_job(
        ctx, person_id, str(snapshot.id), opportunity_id, company_name, job_id=job_id
    )

    assert result["error"] == "processing_failed"
    assert job.status == "failed"
    assert job.phase == "processing"
    assert job.result == result
    assert result["failure_kind"] == "transient"
    assert result["retryable"] is True


@pytest.mark.asyncio
async def test_inbound_parser_keeps_identical_text_on_distinct_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = JobRun(id=uuid.uuid4(), job_type="process_inbound_pitch", attempt=0)
    snapshot = _snapshot()
    session = _session_for(job, snapshot)
    _patch_session(monkeypatch, session)
    monkeypatch.setattr(inbound_job, "get_snapshot", AsyncMock(return_value=b"pdf"))
    monkeypatch.setattr(
        inbound_job,
        "extract_pdf_pages",
        lambda *_args, **_kwargs: [
            ("same text", {"kind": "pdf", "page": 1}),
            ("same text", {"kind": "pdf", "page": 2}),
        ],
    )
    monkeypatch.setattr(inbound_job, "process_candidate_job", AsyncMock(return_value={}))
    ctx, person_id, _snapshot_id, opportunity_id, company_name, job_id = _args(job)

    result = await inbound_job.process_inbound_pitch_job(
        ctx, person_id, str(snapshot.id), opportunity_id, company_name, job_id=job_id
    )

    assert result["observations_created"] == 3
    observations = session.add_all.call_args.args[0]
    assert [observation.source_locator["page"] for observation in observations[:2]] == [1, 2]
