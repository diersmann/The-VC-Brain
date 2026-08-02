"""Tests for the deterministic local demo fixture."""

import hashlib

from scripts.seed_demo import DEMO_RECORDS, _source_content


def test_demo_records_are_unique_and_explicitly_synthetic() -> None:
    stable_ids = [record["stable_id"] for record in DEMO_RECORDS]

    assert len(stable_ids) == len(set(stable_ids))
    assert all(stable_id.startswith("demo:") for stable_id in stable_ids)
    assert all(b"fictional local demo data" in _source_content(record) for record in DEMO_RECORDS)


def test_demo_source_content_is_stable() -> None:
    hashes = [hashlib.sha256(_source_content(record)).hexdigest() for record in DEMO_RECORDS]

    assert hashes == [
        "be17ee81d4a9e34f8591a58ddf1a66bb3ab3f13f762c7258d36da88c9b2530aa",
        "5f021e18d15b679e6cad7ef6d67a9967c0d42e575b8644c8e515ff01ace53ad8",
    ]
