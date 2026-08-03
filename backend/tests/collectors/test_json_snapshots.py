"""Tests for canonical JSON snapshot serialization."""

import json

from app.collectors.base import canonical_json_bytes


def test_canonical_json_round_trips_and_is_stable() -> None:
    value = {"z": "Gründer", "a": [2, {"nested": True}], "empty": None}

    first = canonical_json_bytes(value)
    second = canonical_json_bytes({"empty": None, "a": [2, {"nested": True}], "z": "Gründer"})

    assert first == second
    assert json.loads(first) == value
    assert first == b'{"a":[2,{"nested":true}],"empty":null,"z":"Gr\xc3\xbcnder"}'
