"""Tests for append-only opportunity channel attribution."""

from __future__ import annotations

import uuid

from app.opportunity_service import record_channel_touch


class _Session:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, instance: object) -> None:
        self.added.append(instance)


def test_record_channel_touch_preserves_source_context_without_score_fields() -> None:
    session = _Session()
    opportunity_id = uuid.uuid4()

    touch = record_channel_touch(
        session,
        opportunity_id,
        "search",
        "discovery",
        source_query="climate infrastructure",
        source_ref="profile:123",
        metadata={"provider": "example"},
    )

    assert session.added == [touch]
    assert touch.opportunity_id == opportunity_id
    assert touch.channel == "search"
    assert touch.touch_type == "discovery"
    assert touch.source_query == "climate infrastructure"
    assert touch.source_ref == "profile:123"
    assert touch.touch_metadata == {"provider": "example"}
    assert not hasattr(touch, "score")
