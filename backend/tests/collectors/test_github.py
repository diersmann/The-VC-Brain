"""Tests for the GitHub connector.

Uses respx to mock httpx calls to the GitHub API.
"""

from __future__ import annotations

import pytest
import respx

from app.collectors.base import Seed
from app.collectors.sources.github import GitHubConnector


@pytest.fixture
def connector() -> GitHubConnector:
    return GitHubConnector()


def make_seed(login: str) -> Seed:
    return Seed(source_type="github", handle=login, display_hint=login)


@pytest.mark.asyncio
async def test_discover_returns_seeds(connector: GitHubConnector) -> None:
    """Discover should return Seed objects from search results."""
    with respx.mock:
        respx.get("https://api.github.com/search/users").respond(
            json={
                "items": [
                    {"login": "user1", "id": 1, "gravatar_id": "u1"},
                    {"login": "user2", "id": 2, "gravatar_id": "u2"},
                ]
            }
        )

        seeds = await connector.discover("ml berlin")
        assert len(seeds) == 2
        assert seeds[0].handle == "user1"
        assert seeds[0].source_type == "github"
        assert seeds[1].handle == "user2"


@pytest.mark.asyncio
async def test_discover_rate_limited_returns_empty(connector: GitHubConnector) -> None:
    """Rate-limited responses should return an empty list gracefully."""
    with respx.mock:
        respx.get("https://api.github.com/search/users").respond(status_code=403)

        seeds = await connector.discover("ml berlin")
        assert seeds == []


@pytest.mark.asyncio
async def test_collect_light_returns_collected(connector: GitHubConnector) -> None:
    """Light collect should return a Collected with observations."""
    login = "testuser"
    with respx.mock:
        # User profile
        respx.get(f"https://api.github.com/users/{login}").respond(
            json={
                "login": login,
                "name": "Test User",
                "bio": "ML engineer",
                "location": "Berlin",
                "blog": "https://test.dev",
                "company": "Acme",
                "twitter_username": "testuser",
            }
        )
        # Repos
        respx.get(f"https://api.github.com/users/{login}/repos").respond(
            json=[
                {
                    "name": "repo1",
                    "stargazers_count": 100,
                    "language": "Python",
                    "description": "A cool project",
                },
                {
                    "name": "repo2",
                    "stargazers_count": 50,
                    "language": "Rust",
                    "description": None,
                },
            ]
        )

        seed = make_seed(login)
        collected = await connector.collect(seed, depth="light")

        assert collected.source_type == "github"
        assert collected.uri == f"https://github.com/{login}"
        assert len(collected.observations) > 0

        # Check specific observations
        obs_by_pred: dict[str, str] = {}
        for o in collected.observations:
            pred = str(o.get("predicate", ""))
            val = str(o.get("object_value", ""))
            obs_by_pred[pred] = val

        assert obs_by_pred["github_login"] == login
        assert obs_by_pred["display_name"] == "Test User"
        assert obs_by_pred["github_public_repos"] == "2"
        assert obs_by_pred["github_total_stars"] == "150"
        assert "Python" in obs_by_pred["github_languages"]
        assert "Rust" in obs_by_pred["github_languages"]


@pytest.mark.asyncio
async def test_collect_deep_includes_orgs_and_readme(connector: GitHubConnector) -> None:
    """Deep collect should include org memberships and README."""
    login = "testuser"
    with respx.mock:
        # User profile
        respx.get(f"https://api.github.com/users/{login}").respond(
            json={"login": login, "name": "Test User"}
        )
        # Repos
        respx.get(f"https://api.github.com/users/{login}/repos").respond(
            json=[
                {
                    "name": "top-repo",
                    "stargazers_count": 200,
                    "language": "Python",
                    "description": "Top project",
                    "owner": {"login": login},
                }
            ]
        )
        # Orgs
        respx.get(f"https://api.github.com/users/{login}/orgs").respond(
            json=[{"login": "org1"}, {"login": "org2"}]
        )
        # README
        respx.get(f"https://api.github.com/repos/{login}/top-repo/readme").respond(
            text="# Top Repo\n\nThis is the README content."
        )

        seed = make_seed(login)
        collected = await connector.collect(seed, depth="deep")

        obs: dict[str, str] = {}
        for o in collected.observations:
            pred = str(o.get("predicate", ""))
            val = str(o.get("object_value", ""))
            obs[pred] = val

        assert obs["github_orgs"] == "org1,org2"
        assert "Top Repo" in obs["github_top_repo_readme"]
