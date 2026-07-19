"""Tests for signal score computation."""

from app.collectors.signals import (
    above_threshold,
    arxiv_signal,
    compute_signal_score,
    github_signal,
    producthunt_signal,
    web_signal,
)


def test_github_signal_no_activity() -> None:
    """Zero activity should produce a low signal."""
    score = github_signal(public_repos=0, total_stars=0, top_language_count=0, has_readme=False)
    assert 0.0 <= score < 0.3, f"Expected low signal for no activity, got {score}"


def test_github_signal_high_activity() -> None:
    """High activity should produce a high signal."""
    score = github_signal(public_repos=50, total_stars=5000, top_language_count=5, has_readme=True)
    assert score > 0.5, f"Expected high signal for active profile, got {score}"


def test_producthunt_signal_no_activity() -> None:
    """Zero upvotes should produce a low signal."""
    score = producthunt_signal(total_upvotes=0, launch_count=0, has_maker_profile=False)
    assert 0.0 <= score < 0.3, f"Expected low signal, got {score}"


def test_producthunt_signal_high_activity() -> None:
    """High upvotes should produce a high signal."""
    score = producthunt_signal(total_upvotes=5000, launch_count=5, has_maker_profile=True)
    assert score > 0.5, f"Expected high signal, got {score}"


def test_arxiv_signal_no_papers() -> None:
    """No papers should produce a low signal."""
    score = arxiv_signal(paper_count=0, total_citations=0, in_relevant_categories=False)
    assert 0.0 <= score < 0.3, f"Expected low signal, got {score}"


def test_arxiv_signal_high_impact() -> None:
    """Many papers with citations should produce a high signal."""
    score = arxiv_signal(paper_count=20, total_citations=5000, in_relevant_categories=True)
    assert score > 0.5, f"Expected high signal, got {score}"


def test_web_signal_nothing() -> None:
    """No web presence should produce zero signal."""
    score = web_signal()
    assert score == 0.0


def test_web_signal_full_presence() -> None:
    """Full web presence should produce a high signal."""
    score = web_signal(
        has_company_site=True, has_blog=True,
        has_podcast_appearance=True, has_youtube_talk=True,
    )
    assert score == 1.0


def test_compute_signal_score_combines_components() -> None:
    """compute_signal_score should return a dict with all components and composite."""
    result = compute_signal_score(github=0.8, producthunt=0.5, arxiv=0.3, web=0.2)
    assert "github_signal" in result
    assert "producthunt_signal" in result
    assert "arxiv_signal" in result
    assert "web_signal" in result
    assert "composite" in result
    assert 0.0 < result["composite"] < 1.0


def test_above_threshold_default() -> None:
    """Default threshold of 0.45 should gate correctly."""
    assert above_threshold({"composite": 0.5}, threshold=0.45) is True
    assert above_threshold({"composite": 0.3}, threshold=0.45) is False


def test_above_threshold_custom_threshold() -> None:
    """Custom threshold should work."""
    assert above_threshold({"composite": 0.7}, threshold=0.8) is False
    assert above_threshold({"composite": 0.9}, threshold=0.8) is True
