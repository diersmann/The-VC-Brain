"""Tests for the shared derived-artifact provenance contract."""

import uuid

from app.artifact_provenance import (
    ARTIFACT_PROVENANCE_VERSION,
    build_artifact_metadata,
    fingerprint_payload,
)


def test_fingerprint_is_stable_for_equivalent_payloads() -> None:
    assert fingerprint_payload({"b": 2, "a": [1, 2]}) == fingerprint_payload(
        {"a": [1, 2], "b": 2}
    )


def test_metadata_records_run_versions_inputs_and_validation() -> None:
    run_id = uuid.uuid4()
    metadata = build_artifact_metadata(
        run_id=run_id,
        artifact_type="assessment",
        code_version="research-job-v2",
        input_fingerprint="a" * 64,
        rubric_versions=("opportunity-axes-v1",),
        prompt_version="research-prompts-v1",
        model_version="tavily-search",
        parameters={"axis": "market"},
        latency_ms=42,
        validator_status="passed",
    )

    assert metadata["contract_version"] == ARTIFACT_PROVENANCE_VERSION
    assert metadata["run_id"] == str(run_id)
    assert metadata["input_fingerprint"] == "a" * 64
    assert metadata["validator_status"] == "passed"
    assert metadata["compatibility"] == {"reader": ARTIFACT_PROVENANCE_VERSION}
