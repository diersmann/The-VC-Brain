"""Read-only canonical lifecycle contract for clients and workflow views."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.lifecycle import lifecycle_contract

router = APIRouter(prefix="/lifecycle", tags=["lifecycle"])


class LifecycleStageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    lane: str
    entry_requirements: list[str]
    exit_requirements: list[str]
    actors: list[str]
    transitions: list[str]
    timestamp_source: str


class LifecycleContractResponse(BaseModel):
    version: str
    stages: list[LifecycleStageResponse]


@router.get("", response_model=LifecycleContractResponse)
async def get_lifecycle_contract() -> LifecycleContractResponse:
    """Return the versioned state machine used by backend and workflow UI."""
    payload: dict[str, Any] = lifecycle_contract()
    return LifecycleContractResponse.model_validate(payload)
