"""Tests for append-only public demo evidence import."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts.import_public_inbound import _upsert_observation


def _result(observation: object | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = observation
    return result


@pytest.mark.asyncio
async def test_public_import_does_not_mutate_existing_observation() -> None:
    existing = MagicMock(object_value="same", confidence=0.9)
    session = AsyncMock()
    session.execute.return_value = _result(existing)
    session.add = MagicMock()

    await _upsert_observation(
        session,
        snapshot_id=uuid.uuid4(),
        person_id=uuid.uuid4(),
        opportunity_id=uuid.uuid4(),
        predicate="summary",
        value="same",
        confidence=0.9,
        observed_at=datetime.now(UTC),
    )

    session.add.assert_not_called()
    assert existing.object_value == "same"


@pytest.mark.asyncio
async def test_public_import_appends_correction_observation() -> None:
    existing = MagicMock(object_value="old", confidence=0.9)
    session = AsyncMock()
    session.execute.return_value = _result(existing)
    session.add = MagicMock()

    await _upsert_observation(
        session,
        snapshot_id=uuid.uuid4(),
        person_id=uuid.uuid4(),
        opportunity_id=uuid.uuid4(),
        predicate="summary",
        value="new",
        confidence=0.8,
        observed_at=datetime.now(UTC),
    )

    correction = session.add.call_args.args[0]
    assert correction.object_value == "new"
    assert correction.confidence == 0.8
    assert correction.extractor_version == "public-inbound-v1-correction"
