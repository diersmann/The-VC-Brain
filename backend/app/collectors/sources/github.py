"""GitHub connector — discovers and collects founder data from the GitHub API.

Lightweight discovery: search users by location + topic, return seeds.
Light collect: user profile + top repos metadata.
Deep collect: READMEs, org memberships, recent commit activity.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from app.collectors.base import (
    Collected,
    Connector,
    ConnectorError,
    Depth,
    Seed,
    canonical_json_bytes,
)

logger = structlog.get_logger(__name__)

_API_BASE = "https://api.github.com"
_DEFAULT_PER_PAGE = 30


class GitHubConnector(Connector):
    name = "github"
    source_type = "github"
    authority = 0.8
    cost = 1.0

    def __init__(self) -> None:
        self._token: str | None = None

    def _headers(self) -> dict[str, str]:
        h = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "The-VC-Brain/0.1",
        }
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def _client(self) -> httpx.AsyncClient:
        from app.config import get_settings

        settings = get_settings()
        self._token = settings.github_token or None
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        return httpx.AsyncClient(headers=self._headers(), limits=limits, timeout=15.0)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def discover(self, query: str, page: int = 1) -> list[Seed]:
        """Search GitHub users by location + topic.

        The query is interpreted as a GitHub search::
            location:<query> type:user repos:>0

        Args:
            query: Search query (location).
            page: Page number (1-indexed, 30 results per page).
        """
        search_q = f"location:{query} type:user repos:>0"
        params: dict[str, str | int] = {"q": search_q, "per_page": _DEFAULT_PER_PAGE, "page": page}

        async with await self._client() as client:
            resp = await client.get(f"{_API_BASE}/search/users", params=params)

        if resp.status_code == 403:
            logger.warning("github_rate_limited", reset=resp.headers.get("X-RateLimit-Reset"))
            return []
        if resp.status_code != 200:
            logger.error("github_search_failed", status=resp.status_code, body=resp.text[:500])
            return []

        data = resp.json()
        seeds: list[Seed] = []
        for item in data.get("items", []):
            login = item.get("login", "")
            if login:
                seeds.append(
                    Seed(
                        source_type="github",
                        handle=login,
                        display_hint=login,
                        metadata={"query": query, "gh_id": item.get("id")},
                    )
                )
        return seeds

    # ------------------------------------------------------------------
    # Collect
    # ------------------------------------------------------------------

    async def collect(self, seed: Seed, depth: Depth = "light") -> Collected:
        login = seed.handle
        observations: list[dict[str, object]] = []
        now = datetime.now(UTC)

        async with await self._client() as client:
            # 1. User profile
            user_resp = await client.get(f"{_API_BASE}/users/{login}")
            if user_resp.status_code != 200:
                raise ConnectorError(f"github_user_fetch_failed: {user_resp.status_code}")
            user_data: dict[str, Any] = user_resp.json()

            observations.append(
                {
                    "predicate": "github_login",
                    "object_value": login,
                    "observed_at": now.isoformat(),
                    "confidence": 1.0,
                }
            )
            if user_data.get("name"):
                observations.append(
                    {
                        "predicate": "display_name",
                        "object_value": user_data["name"],
                        "observed_at": now.isoformat(),
                        "confidence": 0.9,
                    }
                )
            if user_data.get("bio"):
                observations.append(
                    {
                        "predicate": "bio",
                        "object_value": user_data["bio"],
                        "observed_at": now.isoformat(),
                        "confidence": 0.8,
                    }
                )
            if user_data.get("location"):
                observations.append(
                    {
                        "predicate": "location",
                        "object_value": user_data["location"],
                        "observed_at": now.isoformat(),
                        "confidence": 0.7,
                    }
                )
            if user_data.get("blog"):
                observations.append(
                    {
                        "predicate": "blog_url",
                        "object_value": user_data["blog"],
                        "observed_at": now.isoformat(),
                        "confidence": 0.9,
                    }
                )
            if user_data.get("company"):
                observations.append(
                    {
                        "predicate": "company",
                        "object_value": user_data["company"],
                        "observed_at": now.isoformat(),
                        "confidence": 0.7,
                    }
                )
            if user_data.get("twitter_username"):
                observations.append(
                    {
                        "predicate": "twitter_handle",
                        "object_value": user_data["twitter_username"],
                        "observed_at": now.isoformat(),
                        "confidence": 0.9,
                    }
                )

            # 2. Repos (light: top 30 by stars; deep: top 50)
            repo_limit = 50 if depth == "deep" else 30
            repos_resp = await client.get(
                f"{_API_BASE}/users/{login}/repos",
                params={"sort": "stars", "per_page": repo_limit, "type": "owner"},
            )
            repos: list[dict[str, Any]] = []
            if repos_resp.status_code == 200:
                repos = repos_resp.json()

            repo_count = len(repos)
            total_stars = sum(r.get("stargazers_count", 0) for r in repos)
            languages: set[str] = set()

            for repo in repos:
                lang = repo.get("language")
                if lang:
                    languages.add(lang)

            observations.append(
                {
                    "predicate": "github_public_repos",
                    "object_value": str(repo_count),
                    "observed_at": now.isoformat(),
                    "confidence": 1.0,
                }
            )
            observations.append(
                {
                    "predicate": "github_total_stars",
                    "object_value": str(total_stars),
                    "observed_at": now.isoformat(),
                    "confidence": 1.0,
                }
            )
            observations.append(
                {
                    "predicate": "github_languages",
                    "object_value": ",".join(sorted(languages)),
                    "observed_at": now.isoformat(),
                    "confidence": 0.9,
                }
            )

            # 3. Deep: org memberships + READMEs
            if depth == "deep":
                # Org memberships
                orgs_resp = await client.get(f"{_API_BASE}/users/{login}/orgs")
                if orgs_resp.status_code == 200:
                    orgs: list[dict[str, Any]] = orgs_resp.json()
                    org_names = [o.get("login", "") for o in orgs if o.get("login")]
                    observations.append(
                        {
                            "predicate": "github_orgs",
                            "object_value": ",".join(org_names),
                            "observed_at": now.isoformat(),
                            "confidence": 0.9,
                        }
                    )

                # README for top repo
                if repos:
                    top_repo = repos[0]
                    owner = top_repo.get("owner", {}).get("login", login)
                    repo_name = top_repo.get("name", "")
                    readme_resp = await client.get(
                        f"{_API_BASE}/repos/{owner}/{repo_name}/readme",
                        params={"Accept": "application/vnd.github.v3.raw"},
                    )
                    if readme_resp.status_code == 200:
                        observations.append(
                            {
                                "predicate": "github_top_repo_readme",
                                "object_value": readme_resp.text[:5000],
                                "observed_at": now.isoformat(),
                                "confidence": 0.8,
                            }
                        )

        # Build the raw JSON payload for the snapshot
        raw_content = {
            "user": user_data,
            "repos": repos,
        }
        raw_bytes = canonical_json_bytes(raw_content)

        return Collected(
            content=raw_bytes,
            content_type="application/json",
            observations=observations,
            source_type="github",
            uri=f"https://github.com/{login}",
            license_hint={"source": "GitHub API", "terms": "https://docs.github.com/en/rest"},
        )
