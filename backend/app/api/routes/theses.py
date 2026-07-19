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
    discovery_queries: list[str] = Field(default_factory=list)
    source_freshness_days: dict[str, int] = Field(default_factory=dict)

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
    discovery_queries: list[str]
    source_freshness_days: dict[str, int]


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


def _generate_discovery_queries(regions: list[Region], sectors: list[Sector]) -> list[str]:
    region_locations = {
        "dach": ["Berlin", "Munich", "Zurich", "Vienna", "Germany", "Switzerland", "Austria"],
        "europe": ["London", "Paris", "Berlin", "Amsterdam", "Stockholm", "Europe"],
        "uk": ["London", "Manchester", "Cambridge", "Oxford", "United Kingdom"],
        "us": ["San Francisco", "New York", "Seattle", "Austin", "Boston", "United States"],
        "global": ["San Francisco", "London", "Berlin", "New York", "Singapore"],
    }
    sector_terms = {
        "ai": ["AI", "machine-learning", "deep-learning"],
        "deep-tech": ["robotics", "quantum", "semiconductor"],
        "b2b": ["SaaS", "B2B", "enterprise"],
        "climate": ["climate-tech", "sustainability"],
        "fintech": ["fintech", "blockchain", "crypto"],
        "health": ["biotech", "digital-health"],
    }
    
    locations = []
    for r in regions:
        locations.extend(region_locations.get(r, []))
    locations = list(dict.fromkeys(locations))
    
    terms = []
    for s in sectors:
        terms.extend(sector_terms.get(s, []))
    terms = list(dict.fromkeys(terms))
    
    if not locations:
        locations = ["Berlin", "London", "San Francisco"]
        
    if not terms:
        return locations
        
    queries = []
    for loc in locations:
        for term in terms:
            queries.append(f"{loc} {term}")
            
    return queries[:20]


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
    
    stages = list(dict.fromkeys(body.stages))
    sectors = list(dict.fromkeys(body.sectors))
    regions = list(dict.fromkeys(body.regions))
    
    discovery_queries = body.discovery_queries
    if not discovery_queries:
        discovery_queries = _generate_discovery_queries(regions, sectors)
        
    thesis = InvestmentThesis(
        version=f"thesis-v{version_number:03d}",
        name=body.name,
        is_active=True,
        stages=stages,
        sectors=sectors,
        excluded_sectors=list(dict.fromkeys(body.excluded_sectors)),
        regions=regions,
        check_size_min_k_eur=body.check_size_min_k_eur,
        check_size_max_k_eur=body.check_size_max_k_eur,
        ownership_target_pct=body.ownership_target_pct,
        risk_appetite=body.risk_appetite,
        scoring_weights=body.scoring_weights,
        discovery_queries=discovery_queries,
        source_freshness_days=body.source_freshness_days,
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
