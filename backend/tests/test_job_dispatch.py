"""Tests for preserving durable job IDs across Redis-to-Arq dispatch."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.collectors.jobs import enqueue_arq_job


@pytest.mark.asyncio
async def test_score_job_dispatch_forwards_job_id() -> None:
    pool = AsyncMock()

    await enqueue_arq_job(
        {"redis": pool},
        {"job_type": "score_candidate", "person_id": "person-1", "job_id": "job-1"},
    )

    pool.enqueue_job.assert_awaited_once_with("score_candidate_job", "person-1", "job-1")


@pytest.mark.asyncio
async def test_discover_job_dispatch_forwards_job_id() -> None:
    pool = AsyncMock()

    await enqueue_arq_job(
        {"redis": pool},
        {
            "job_type": "discover",
            "query": "AI founders",
            "source": "github",
            "job_id": "job-1",
        },
    )

    pool.enqueue_job.assert_awaited_once_with(
        "discover_job", "AI founders", "github", "job-1"
    )


@pytest.mark.asyncio
async def test_memo_job_dispatch_forwards_job_id() -> None:
    pool = AsyncMock()

    await enqueue_arq_job(
        {"redis": pool},
        {
            "job_type": "generate_memo",
            "person_id": "person-1",
            "opportunity_id": "opportunity-1",
            "job_id": "job-1",
        },
    )

    pool.enqueue_job.assert_awaited_once_with(
        "generate_memo_job", "person-1", "opportunity-1", "job-1"
    )


@pytest.mark.asyncio
async def test_research_job_dispatch_forwards_job_id() -> None:
    pool = AsyncMock()

    await enqueue_arq_job(
        {"redis": pool},
        {
            "job_type": "research_candidate",
            "person_id": "person-1",
            "opportunity_id": "opportunity-1",
            "job_id": "job-1",
        },
    )

    pool.enqueue_job.assert_awaited_once_with(
        "research_candidate_job", "person-1", "opportunity-1", "job-1"
    )


@pytest.mark.asyncio
async def test_collect_job_dispatch_forwards_optional_job_id() -> None:
    pool = AsyncMock()

    await enqueue_arq_job(
        {"redis": pool},
        {
            "person_id": "person-1",
            "source": "github",
            "depth": "deep",
            "handle": "founder",
            "job_id": "job-1",
        },
    )

    pool.enqueue_job.assert_awaited_once_with(
        "collect_job", "person-1", "github", "deep", "founder", "job-1"
    )


@pytest.mark.asyncio
async def test_avatar_job_dispatch_forwards_optional_job_id() -> None:
    pool = AsyncMock()

    await enqueue_arq_job(
        {"redis": pool},
        {"job_type": "fetch_candidate_avatar", "person_id": "person-1", "job_id": "job-1"},
    )

    pool.enqueue_job.assert_awaited_once_with(
        "fetch_candidate_avatar_job", "person-1", "job-1"
    )


@pytest.mark.asyncio
async def test_processing_job_dispatch_forwards_optional_job_id() -> None:
    pool = AsyncMock()

    await enqueue_arq_job(
        {"redis": pool},
        {"job_type": "process_candidate", "person_id": "person-1", "job_id": "job-1"},
    )

    pool.enqueue_job.assert_awaited_once_with("process_candidate_job", "person-1", "job-1")


@pytest.mark.asyncio
async def test_inbound_processing_dispatch_forwards_optional_job_id() -> None:
    pool = AsyncMock()

    await enqueue_arq_job(
        {"redis": pool},
        {
            "job_type": "process_inbound_pitch",
            "person_id": "person-1",
            "snapshot_id": "snapshot-1",
            "opportunity_id": "opportunity-1",
            "company_name": "Acme",
            "founder_evidence": {"learning_velocity": "Built a prototype"},
            "job_id": "job-1",
        },
    )

    pool.enqueue_job.assert_awaited_once_with(
        "process_inbound_pitch_job",
        "person-1",
        "snapshot-1",
        "opportunity-1",
        "Acme",
        {"learning_velocity": "Built a prototype"},
        "job-1",
    )


@pytest.mark.asyncio
async def test_identity_job_dispatch_forwards_optional_job_id() -> None:
    pool = AsyncMock()

    await enqueue_arq_job(
        {"redis": pool},
        {"job_type": "resolve_identities", "job_id": "job-1"},
    )

    pool.enqueue_job.assert_awaited_once_with("resolve_identities_job", "job-1")
