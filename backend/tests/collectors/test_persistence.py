"""Tests for content-addressed collection persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.collectors.jobs import _write_observations, _write_snapshot
from app.collectors.persistence import (
    observation_persistence_fingerprint,
    snapshot_persistence_fingerprint,
)
from app.db.models import Observation, SourceSnapshot


class _NestedTransaction:
    async def __aenter__(self) -> _NestedTransaction:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None


def _session_with_nested() -> AsyncMock:
    session = AsyncMock()
    session.begin_nested = MagicMock(return_value=_NestedTransaction())
    session.add = MagicMock()
    return session


def test_snapshot_fingerprint_is_unambiguous_for_control_text() -> None:
    assert snapshot_persistence_fingerprint("a\x1fb", "c", "d") != snapshot_persistence_fingerprint(
        "a", "b\x1fc", "d"
    )


def _result(value: object | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_write_snapshot_reuses_identical_content() -> None:
    existing = SourceSnapshot(
        id=uuid.uuid4(),
        uri="https://example.test",
        source_type="website",
        content_hash="hash-1",
        storage_path="website/hash-1",
        collected_at=datetime.now(UTC),
    )
    session = AsyncMock()
    session.execute.return_value = _result(existing)
    session.add = MagicMock()

    with patch(
        "app.collectors.jobs.put_snapshot",
        new=AsyncMock(return_value=("hash-1", "website/hash-1")),
    ):
        result = await _write_snapshot(
            session,
            MagicMock(
                content=b"same",
                content_type="text/html",
                source_type="website",
                uri="https://example.test",
                license_hint=None,
            ),
        )

    assert result is existing
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_write_snapshot_sets_database_dedupe_fingerprint() -> None:
    session = _session_with_nested()
    session.execute.return_value = _result(None)

    with patch(
        "app.collectors.jobs.put_snapshot",
        new=AsyncMock(return_value=("hash-1", "website/hash-1")),
    ):
        await _write_snapshot(
            session,
            MagicMock(
                content=b"same",
                content_type="text/html",
                source_type="website",
                uri="https://example.test",
                license_hint=None,
            ),
        )

    snapshot = session.add.call_args.args[0]
    assert snapshot.persistence_fingerprint == snapshot_persistence_fingerprint(
        "https://example.test", "website", "hash-1"
    )


@pytest.mark.asyncio
async def test_write_observations_skips_identical_rows() -> None:
    existing = Observation(
        id=uuid.uuid4(),
        snapshot_id=uuid.uuid4(),
        subject_id=uuid.uuid4(),
        predicate="title",
        object_value="Example",
        observed_at=datetime.now(UTC),
        extractor_version="website-v1",
        confidence=1.0,
    )
    session = AsyncMock()
    session.execute.return_value = _result(existing)
    session.add = MagicMock()

    ids = await _write_observations(
        session,
        MagicMock(id=existing.snapshot_id, source_type="website"),
        [{"predicate": "title", "object_value": "Example", "confidence": 1.0}],
        existing.subject_id,
    )

    assert ids == [existing.id]
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_write_observations_sets_database_dedupe_fingerprint() -> None:
    session = _session_with_nested()
    session.execute.return_value = _result(None)
    snapshot_id = uuid.uuid4()
    subject_id = uuid.uuid4()
    opportunity_id = uuid.uuid4()

    ids = await _write_observations(
        session,
        MagicMock(id=snapshot_id, source_type="website", uri="https://example.test"),
        [{"predicate": "title", "object_value": "Example", "confidence": 1.0}],
        subject_id,
        opportunity_id,
    )

    observation = session.add.call_args.args[0]
    assert ids == [observation.id]
    assert observation.persistence_fingerprint == observation_persistence_fingerprint(
        snapshot_id=snapshot_id,
        subject_id=subject_id,
        opportunity_id=opportunity_id,
        predicate="title",
        object_value="Example",
        extractor_version="website-v1",
    )


@pytest.mark.asyncio
async def test_write_snapshot_reuses_winner_after_unique_race() -> None:
    from sqlalchemy.exc import IntegrityError

    existing = SourceSnapshot(
        id=uuid.uuid4(),
        uri="https://example.test",
        source_type="website",
        content_hash="hash-1",
        storage_path="website/hash-1",
        collected_at=datetime.now(UTC),
    )
    session = _session_with_nested()
    session.execute.side_effect = [_result(None), _result(existing)]
    session.flush.side_effect = IntegrityError("duplicate", {}, Exception())

    with patch(
        "app.collectors.jobs.put_snapshot",
        new=AsyncMock(return_value=("hash-1", "website/hash-1")),
    ):
        result = await _write_snapshot(
            session,
            MagicMock(
                content=b"same",
                content_type="text/html",
                source_type="website",
                uri="https://example.test",
                license_hint=None,
            ),
        )

    assert result is existing


@pytest.mark.asyncio
async def test_write_observations_reuses_winner_after_unique_race() -> None:
    from sqlalchemy.exc import IntegrityError

    snapshot_id = uuid.uuid4()
    subject_id = uuid.uuid4()
    existing = Observation(
        id=uuid.uuid4(),
        snapshot_id=snapshot_id,
        subject_id=subject_id,
        predicate="title",
        object_value="Example",
        observed_at=datetime.now(UTC),
        extractor_version="website-v1",
        confidence=1.0,
    )
    session = _session_with_nested()
    session.execute.side_effect = [_result(None), _result(existing)]
    session.flush.side_effect = IntegrityError("duplicate", {}, Exception())

    ids = await _write_observations(
        session,
        MagicMock(id=snapshot_id, source_type="website", uri="https://example.test"),
        [{"predicate": "title", "object_value": "Example", "confidence": 1.0}],
        subject_id,
    )

    assert ids == [existing.id]


@pytest.mark.asyncio
async def test_write_observations_rejects_invalid_schema_values() -> None:
    session = AsyncMock()
    session.add = MagicMock()

    ids = await _write_observations(
        session,
        MagicMock(id=uuid.uuid4(), source_type="website", uri="https://example.test"),
        [
            {"predicate": "", "object_value": "value"},
            {"predicate": "title", "object_value": "", "confidence": 2.0},
        ],
        uuid.uuid4(),
    )

    assert ids == []
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_write_observations_rejects_invalid_and_future_times() -> None:
    session = AsyncMock()
    session.add = MagicMock()

    ids = await _write_observations(
        session,
        MagicMock(id=uuid.uuid4(), source_type="website", uri="https://example.test"),
        [
            {"predicate": "title", "object_value": "Example", "observed_at": "not-a-date"},
            {
                "predicate": "title",
                "object_value": "Example",
                "observed_at": datetime.now(UTC) + timedelta(minutes=6),
            },
        ],
        uuid.uuid4(),
    )

    assert ids == []
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_write_observations_records_coordinate_gap_metadata() -> None:
    session = AsyncMock()
    session.execute.return_value = _result(None)
    session.add = MagicMock()

    await _write_observations(
        session,
        MagicMock(id=uuid.uuid4(), source_type="website", uri="https://example.test"),
        [{"predicate": "title", "object_value": "Example"}],
        uuid.uuid4(),
    )

    observation = session.add.call_args.args[0]
    assert observation.source_locator["reason"] == "coordinate unavailable from connector"
