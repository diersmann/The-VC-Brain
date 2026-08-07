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
