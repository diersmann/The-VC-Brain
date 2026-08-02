"""Tests for content-addressed collection persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.collectors.jobs import _write_observations, _write_snapshot
from app.db.models import Observation, SourceSnapshot


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
