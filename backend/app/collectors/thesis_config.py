"""Thesis configuration loader.

Loads a YAML file defining per-source thresholds, search queries,
arXiv categories, coauthor caps, and Tavily budget.

If no file is present, falls back to env defaults from ``Settings``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import structlog
import yaml  # type: ignore[import-untyped]

from app.config import get_settings

logger = structlog.get_logger(__name__)

_THESIS_PATH = Path(__file__).resolve().parent.parent.parent / "thesis.yaml"


# ---------------------------------------------------------------------------
# Defaults (mirror Settings)
# ---------------------------------------------------------------------------

_DEFAULTS: dict[str, Any] = {
    "signal_threshold": 0.45,
    "collection_concurrency": 4,
    "tavily_monthly_budget": 1000,
    "arxiv_min_citations": 10,
    "arxiv_coauthor_cap": 20,
    "website_seed_cap": 10,
    "persons_created_per_day": 200,
    "arxiv_categories": [
        "cs.AI",
        "cs.LG",
        "cs.CL",
        "cs.CV",
        "cs.SE",
        "cs.IR",
        "cs.NE",
        "cs.RO",
        "stat.ML",
    ],
    "discovery_queries": [
        "AI infrastructure founder",
        "machine learning startup",
        "developer tools founder",
        "SaaS founder Berlin",
    ],
    "source_freshness_days": {
        "github": 7,
        "producthunt": 14,
        "arxiv": 30,
        "web": 30,
        "hackernews": 7,
    },
}


def _load_yaml() -> dict[str, Any] | None:
    """Load thesis.yaml if it exists, return None otherwise."""
    if not _THESIS_PATH.exists():
        return None
    try:
        with open(_THESIS_PATH) as f:
            result = cast(dict[str, Any] | None, yaml.safe_load(f))
            return result
    except Exception as exc:
        logger.warning("thesis_yaml_load_failed", path=str(_THESIS_PATH), error=str(exc))
        return None


def get_thesis_config() -> dict[str, Any]:
    """Return the merged thesis configuration.

    Values from thesis.yaml override env defaults.
    """
    overrides = _load_yaml() or {}
    config = dict(_DEFAULTS)
    config.update(overrides)

    # Env settings always win for sensitive/secret values
    settings = get_settings()
    config["signal_threshold"] = settings.signal_threshold
    config["collection_concurrency"] = settings.collection_concurrency
    config["tavily_monthly_budget"] = settings.tavily_monthly_budget
    config["arxiv_min_citations"] = settings.arxiv_min_citations
    config["arxiv_coauthor_cap"] = settings.arxiv_coauthor_cap
    config["website_seed_cap"] = settings.website_seed_cap
    config["persons_created_per_day"] = settings.persons_created_per_day

    return config
