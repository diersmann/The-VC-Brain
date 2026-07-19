"""Tests for identity matchers."""

from __future__ import annotations

from typing import Any

from app.identity.matchers import (
    _normalize_url,
    match_confidence,
    should_auto_merge,
)


def _obs(*pairs: str) -> list[dict[str, Any]]:
    """Helper: build observation list from predicate, value pairs."""
    it = iter(pairs)
    return [{"predicate": p, "object_value": v} for p, v in zip(it, it, strict=True)]


def test_normalize_url_strips_scheme_and_www() -> None:
    assert _normalize_url("https://www.tiangolo.com") == "tiangolo.com"
    assert _normalize_url("http://tiangolo.com") == "tiangolo.com"
    assert _normalize_url("https://tiangolo.com/") == "tiangolo.com"


def test_normalize_url_preserves_path() -> None:
    assert _normalize_url("https://tiangolo.com/blog") == "tiangolo.com/blog"
    assert _normalize_url("https://tiangolo.com/blog/") == "tiangolo.com/blog"


def test_normalize_url_lowercases() -> None:
    assert _normalize_url("HTTPS://Tiangolo.COM") == "tiangolo.com"


# ---------------------------------------------------------------------------
# Email exact match
# ---------------------------------------------------------------------------


def test_email_exact_match() -> None:
    """Same email should return confidence 1.0."""
    confidence, reasons = match_confidence(
        _obs("email", "sebastian@tiangolo.com"),
        _obs("email", "sebastian@tiangolo.com"),
    )
    assert confidence == 1.0
    assert "email_exact" in reasons


def test_email_case_insensitive() -> None:
    """Email matching should be case-insensitive."""
    confidence, _ = match_confidence(
        _obs("email", "Sebastian@Tiangolo.com"),
        _obs("email", "sebastian@tiangolo.com"),
    )
    assert confidence == 1.0


# ---------------------------------------------------------------------------
# Twitter handle exact match
# ---------------------------------------------------------------------------


def test_twitter_exact_match() -> None:
    """Same Twitter handle should return confidence 0.95."""
    confidence, reasons = match_confidence(
        _obs("twitter_handle", "tiangolo"),
        _obs("twitter_handle", "tiangolo"),
    )
    assert confidence == 0.95
    assert "twitter_exact" in reasons


# ---------------------------------------------------------------------------
# URL exact match
# ---------------------------------------------------------------------------


def test_blog_website_url_match() -> None:
    """Blog URL from GitHub matching website URL from ProductHunt."""
    confidence, reasons = match_confidence(
        _obs("blog_url", "https://tiangolo.com"),
        _obs("website_url", "https://www.tiangolo.com"),
    )
    assert confidence == 0.95
    assert "url_exact" in reasons


def test_website_blog_url_match_reverse() -> None:
    """Website URL from A matching blog URL from B."""
    confidence, _ = match_confidence(
        _obs("website_url", "https://tiangolo.com"),
        _obs("blog_url", "https://tiangolo.com"),
    )
    assert confidence == 0.95


# ---------------------------------------------------------------------------
# Name similarity + corroboration
# ---------------------------------------------------------------------------


def test_name_fuzzy_with_location() -> None:
    """Similar name + same location should return confidence 0.85."""
    confidence, reasons = match_confidence(
        _obs("display_name", "Sebastián Ramírez", "location", "Berlin, Germany"),
        _obs("display_name", "Sebastian Ramirez", "location", "Berlin, Germany"),
    )
    assert confidence == 0.85
    assert "name_fuzzy" in reasons
    assert "same_location" in reasons


def test_name_fuzzy_with_company() -> None:
    """Similar name + same company should return confidence 0.85."""
    confidence, reasons = match_confidence(
        _obs("display_name", "Sebastián Ramírez", "company", "FastAPI Cloud"),
        _obs("display_name", "Sebastian Ramirez", "company", "FastAPI Cloud"),
    )
    assert confidence == 0.85
    assert "same_company" in reasons


def test_name_fuzzy_no_corroboration() -> None:
    """Similar name without corroboration should return confidence 0.5."""
    confidence, reasons = match_confidence(
        _obs("display_name", "Sebastián Ramírez"),
        _obs("display_name", "Sebastian Ramirez"),
    )
    assert confidence == 0.5
    assert "name_fuzzy_only" in reasons


def test_different_names_no_match() -> None:
    """Completely different names should return confidence 0.0."""
    confidence, _ = match_confidence(
        _obs("display_name", "Alice Smith"),
        _obs("display_name", "Bob Jones"),
    )
    assert confidence == 0.0


# ---------------------------------------------------------------------------
# should_auto_merge
# ---------------------------------------------------------------------------


def test_should_auto_merge_above_threshold() -> None:
    assert should_auto_merge(0.85) is True
    assert should_auto_merge(0.95) is True
    assert should_auto_merge(1.0) is True


def test_should_auto_merge_below_threshold() -> None:
    assert should_auto_merge(0.5) is False
    assert should_auto_merge(0.0) is False


def test_should_auto_merge_custom_threshold() -> None:
    assert should_auto_merge(0.7, threshold=0.6) is True
    assert should_auto_merge(0.5, threshold=0.6) is False


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_observations() -> None:
    """No observations should return confidence 0.0."""
    confidence, _ = match_confidence([], [])
    assert confidence == 0.0


def test_missing_predicate() -> None:
    """Observations without expected predicates should not crash."""
    confidence, _ = match_confidence(
        _obs("unknown", "something"),
        _obs("other", "else"),
    )
    assert confidence == 0.0


def test_linkedin_name_match() -> None:
    """LinkedIn URL containing the display name should corroborate."""
    confidence, reasons = match_confidence(
        _obs("display_name", "Sebastián Ramírez", "location", "Berlin"),
        _obs("display_name", "Sebastian Ramirez", "linkedin_url", "https://linkedin.com/in/sebastian-ramirez"),
    )
    assert confidence == 0.85
    assert "linkedin_name_match" in reasons
