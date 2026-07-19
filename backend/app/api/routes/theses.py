"""Versioned investment thesis configuration and deterministic rescoring."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.db.models import InvestmentThesis
from app.scoring.thesis import DEFAULT_WEIGHTS, score_all_candidates

router = APIRouter(prefix="/theses", tags=["theses"])

Stage = Literal["pre-seed", "seed", "series-a", "series-b", "series-c"]
Sector = Literal["ai", "deep-tech", "b2b", "climate", "fintech", "health"]
Region = Literal["dach", "europe", "uk", "us", "global"]
RiskAppetite = Literal["conservative", "balanced", "bold"]


class ThesisRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    stages: list[Stage] = Field(min_length=1)
    sectors: list[Sector] = Field(min_length=1)
    excluded_sectors: list[Sector] = Field(default_factory=list)
    regions: list[Region] = Field(min_length=1)
    check_size_min_k_eur: float | None = Field(default=None, ge=0)
    check_size_max_k_eur: float | None = Field(default=None, ge=0)
    ownership_target_pct: float | None = Field(default=10.0, ge=0, le=100)
    risk_appetite: RiskAppetite = "balanced"
    scoring_weights: dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    @model_validator(mode="after")
    def validate_thesis(self) -> ThesisRequest:
        if (
            self.check_size_min_k_eur is not None
            and self.check_size_max_k_eur is not None
            and self.check_size_min_k_eur > self.check_size_max_k_eur
        ):
            raise ValueError("Minimum check size cannot exceed maximum check size")
        if set(self.scoring_weights) != set(DEFAULT_WEIGHTS):
            raise ValueError(f"Scoring weights must contain {sorted(DEFAULT_WEIGHTS)}")
        if any(value < 0 for value in self.scoring_weights.values()):
            raise ValueError("Scoring weights cannot be negative")
        if sum(self.scoring_weights.values()) <= 0:
            raise ValueError("At least one scoring weight must be positive")
        overlap = set(self.sectors) & set(self.excluded_sectors)
        if overlap:
            raise ValueError(f"Preferred and excluded sectors overlap: {sorted(overlap)}")
        return self


class ThesisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: str
    name: str
    is_active: bool
    stages: list[str]
    sectors: list[str]
    excluded_sectors: list[str]
    regions: list[str]
    check_size_min_k_eur: float | None
    check_size_max_k_eur: float | None
    ownership_target_pct: float | None
    risk_appetite: str
    scoring_weights: dict[str, float]


class ThesisSaveResponse(BaseModel):
    thesis: ThesisResponse
    scored_candidates: int


async def _active_thesis(session: AsyncSession) -> InvestmentThesis | None:
    result = await session.execute(
        select(InvestmentThesis)
        .where(InvestmentThesis.is_active.is_(True))
        .order_by(InvestmentThesis.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/active", response_model=ThesisResponse)
async def get_active_thesis(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InvestmentThesis:
    thesis = await _active_thesis(session)
    if thesis is None:
        raise HTTPException(status_code=404, detail="No active investment thesis")
    return thesis


@router.post("/active", response_model=ThesisSaveResponse)
async def save_active_thesis(
    body: ThesisRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ThesisSaveResponse:
    """Create an immutable thesis version, activate it and rescore all candidates."""
    count_result = await session.execute(select(func.count(InvestmentThesis.id)))
    version_number = int(count_result.scalar_one()) + 1
    await session.execute(
        update(InvestmentThesis)
        .where(InvestmentThesis.is_active.is_(True))
        .values(is_active=False)
    )
    thesis = InvestmentThesis(
        version=f"thesis-v{version_number:03d}",
        name=body.name,
        is_active=True,
        stages=list(dict.fromkeys(body.stages)),
        sectors=list(dict.fromkeys(body.sectors)),
        excluded_sectors=list(dict.fromkeys(body.excluded_sectors)),
        regions=list(dict.fromkeys(body.regions)),
        check_size_min_k_eur=body.check_size_min_k_eur,
        check_size_max_k_eur=body.check_size_max_k_eur,
        ownership_target_pct=body.ownership_target_pct,
        risk_appetite=body.risk_appetite,
        scoring_weights=body.scoring_weights,
    )
    session.add(thesis)
    await session.flush()
    scored = await score_all_candidates(session, thesis)
    await session.commit()
    await session.refresh(thesis)
    return ThesisSaveResponse(
        thesis=ThesisResponse.model_validate(thesis), scored_candidates=scored
    )


@router.post("/active/score", response_model=ThesisSaveResponse)
async def rescore_active_thesis(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ThesisSaveResponse:
    thesis = await _active_thesis(session)
    if thesis is None:
        raise HTTPException(status_code=404, detail="No active investment thesis")
    scored = await score_all_candidates(session, thesis)
    await session.commit()
    return ThesisSaveResponse(
        thesis=ThesisResponse.model_validate(thesis), scored_candidates=scored
    )
