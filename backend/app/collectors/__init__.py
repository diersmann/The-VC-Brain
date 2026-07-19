"""Data collector package — multi-source founder discovery and collection.

Sources:
    github          — GitHub API (repos, stars, orgs, READMEs)
    producthunt     — Product Hunt GraphQL API (posts, makers, upvotes)
    arxiv           — arXiv API + Semantic Scholar citations (papers, coauthors)
    web             — Generic website via Tavily Extract / HTTP fallback
    tavily_search   — Tavily Search for open-web discovery
    hackernews      — Algolia HN API (submissions, comments) — Phase 1
    youtube         — YouTube Data API — Phase 2 stub
    podcasts        — RSS/transcript discovery — Phase 2 stub
    hackathons      — Devpost/MLH via Tavily — Phase 2 stub
    linkedin        — Tavily search only — Phase 2 stub
"""

from app.collectors.base import Collected, Connector, ConnectorError, Depth, Seed
from app.collectors.registry import all_connectors, get_connector

__all__ = [
    "Collected",
    "Connector",
    "ConnectorError",
    "Depth",
    "Seed",
    "all_connectors",
    "get_connector",
]
