"""Pure functions for computing a person's SignalScore from observations.

The SignalScore is a lightweight first-pass score that determines whether
a person should be escalated to deep collection.  It is stored as a
ScoreSnapshot with rubric_version="signal-v1".

Components (all in [0, 1]):
    github_signal
    producthunt_signal
    arxiv_signal
    web_signal
    composite  (weighted combination)
"""

from __future__ import annotations

import math

# Weights for the composite score (tunable, sum to 1.0).
_COMPOSITE_WEIGHTS: dict[str, float] = {
    "github_signal": 0.35,
    "producthunt_signal": 0.25,
    "arxiv_signal": 0.20,
    "web_signal": 0.20,
}


def _sigmoid(x: float, midpoint: float = 0.0, steepness: float = 1.0) -> float:
    """Squash a raw value into [0, 1] using a sigmoid."""
    return 1.0 / (1.0 + math.exp(-steepness * (x - midpoint)))


def github_signal(
    public_repos: int = 0,
    total_stars: int = 0,
    top_language_count: int = 0,
    has_readme: bool = False,
) -> float:
    """Compute a GitHub signal score from lightweight metadata.

    Args:
        public_repos: Number of public repos.
        total_stars: Sum of stars across all repos.
        top_language_count: Number of distinct languages in top repos.
        has_readme: Whether the primary repo has a README.
    """
    repo_score = _sigmoid(public_repos, midpoint=5, steepness=0.3)
    star_score = _sigmoid(math.log1p(total_stars), midpoint=3, steepness=0.5)
    lang_score = _sigmoid(top_language_count, midpoint=2, steepness=0.5)
    readme_score = 0.2 if has_readme else 0.0

    return 0.3 * repo_score + 0.4 * star_score + 0.2 * lang_score + 0.1 * readme_score


def producthunt_signal(
    total_upvotes: int = 0,
    launch_count: int = 0,
    has_maker_profile: bool = False,
) -> float:
    """Compute a Product Hunt signal score."""
    upvote_score = _sigmoid(math.log1p(total_upvotes), midpoint=4, steepness=0.4)
    launch_score = _sigmoid(launch_count, midpoint=1, steepness=1.0)
    profile_score = 0.3 if has_maker_profile else 0.0

    return 0.5 * upvote_score + 0.3 * launch_score + 0.2 * profile_score


def arxiv_signal(
    paper_count: int = 0,
    total_citations: int = 0,
    in_relevant_categories: bool = False,
) -> float:
    """Compute an arXiv signal score."""
    paper_score = _sigmoid(paper_count, midpoint=3, steepness=0.4)
    citation_score = _sigmoid(math.log1p(total_citations), midpoint=3, steepness=0.5)
    category_boost = 0.2 if in_relevant_categories else 0.0

    return 0.4 * paper_score + 0.4 * citation_score + 0.2 * category_boost


def web_signal(
    has_company_site: bool = False,
    has_blog: bool = False,
    has_podcast_appearance: bool = False,
    has_youtube_talk: bool = False,
) -> float:
    """Compute a web / general signal score."""
    score = 0.0
    if has_company_site:
        score += 0.3
    if has_blog:
        score += 0.2
    if has_podcast_appearance:
        score += 0.25
    if has_youtube_talk:
        score += 0.25
    return min(1.0, score)


def compute_signal_score(
    github: float = 0.0,
    producthunt: float = 0.0,
    arxiv: float = 0.0,
    web: float = 0.0,
) -> dict[str, float]:
    """Compute the full signal scorecard for a person.

    Returns a dict suitable for ScoreSnapshot.components.
    """
    components: dict[str, float] = {
        "github_signal": round(github, 4),
        "producthunt_signal": round(producthunt, 4),
        "arxiv_signal": round(arxiv, 4),
        "web_signal": round(web, 4),
    }

    # Missing sources reduce coverage/confidence, not candidate quality.
    # Normalize the composite over sources that actually supplied a signal.
    available = {
        key: weight
        for key, weight in _COMPOSITE_WEIGHTS.items()
        if components.get(key, 0.0) > 0.0
    }
    available_weight = sum(available.values())
    composite = (
        sum(components[key] * weight for key, weight in available.items())
        / available_weight
        if available_weight
        else 0.0
    )
    components["composite"] = round(composite, 4)
    components["signal_coverage"] = round(available_weight, 4)
    return components


def above_threshold(
    signal_components: dict[str, float],
    threshold: float = 0.45,
) -> bool:
    """Return True if the composite signal score meets or exceeds the threshold."""
    return signal_components.get("composite", 0.0) >= threshold
