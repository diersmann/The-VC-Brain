"""Pure matching functions for identity resolution.

Each function takes observation data from two Person records and returns
a confidence score (0.0-1.0) and a list of reasons.

Matching rules (in order of strength):
    - Email exact match → 1.0
    - Twitter handle exact match → 0.95
    - Blog/website URL exact match (normalized) → 0.95
    - Name similarity ≥ 90 + ≥1 corroborating signal → 0.85
    - Name similarity ≥ 90, no corroboration → 0.5 (flagged for review)
    - Otherwise → 0.0
"""

from __future__ import annotations

import unicodedata
from urllib.parse import urlparse

from rapidfuzz import fuzz

# ---------------------------------------------------------------------------
# URL normalization
# ---------------------------------------------------------------------------


def _normalize_url(url: str) -> str:
    """Normalize a URL for comparison: strip scheme, www, trailing slash."""
    url = url.strip().lower()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    # Remove www. prefix
    if hostname.startswith("www."):
        hostname = hostname[4:]
    path = parsed.path.rstrip("/")
    return f"{hostname}{path}"


# ---------------------------------------------------------------------------
# Signal extractors
# ---------------------------------------------------------------------------


def _get_observation(
    observations: list[dict[str, object]], predicate: str
) -> str | None:
    """Return the object_value of the first observation matching *predicate*."""
    for obs in observations:
        if obs.get("predicate") == predicate:
            val = obs.get("object_value")
            if val:
                return str(val).strip()
    return None


def _extract_signals(
    observations: list[dict[str, object]],
) -> dict[str, str | None]:
    """Extract identity-relevant signals from a person's observations.

    Returns a dict with keys: email, twitter_handle, blog_url, website_url,
    display_name, location, company, linkedin_url, github_login.
    """
    return {
        "email": _get_observation(observations, "email"),
        "twitter_handle": _get_observation(observations, "twitter_handle"),
        "blog_url": _get_observation(observations, "blog_url"),
        "website_url": _get_observation(observations, "website_url"),
        "display_name": _get_observation(observations, "display_name"),
        "location": _get_observation(observations, "location"),
        "company": _get_observation(observations, "company"),
        "linkedin_url": _get_observation(observations, "linkedin_url"),
        "github_login": _get_observation(observations, "github_login"),
    }


# ---------------------------------------------------------------------------
# Matchers
# ---------------------------------------------------------------------------


def _exact_match(a: str | None, b: str | None) -> bool:
    """Case-insensitive, trimmed equality."""
    if not a or not b:
        return False
    return a.strip().lower() == b.strip().lower()


def _url_match(a: str | None, b: str | None) -> bool:
    """Normalized URL equality."""
    if not a or not b:
        return False
    return _normalize_url(a) == _normalize_url(b)


def _normalize_name(name: str) -> str:
    """Strip diacritics/accents and lowercase for fuzzy matching."""
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _name_similarity(a: str | None, b: str | None) -> float:
    """Token-sort ratio via rapidfuzz, returns 0-100.

    Accents are normalized before comparison so 'é' matches 'e'.
    """
    if not a or not b:
        return 0.0
    return fuzz.token_sort_ratio(_normalize_name(a), _normalize_name(b))


def _corroborating_signals(
    signals_a: dict[str, str | None],
    signals_b: dict[str, str | None],
) -> list[str]:
    """Return a list of corroborating signal names.

    Checks: same location, same company, same blog domain,
    linkedin_url contains display_name, etc.
    """
    reasons: list[str] = []

    # Same location
    if _exact_match(signals_a.get("location"), signals_b.get("location")):
        reasons.append("same_location")

    # Same company
    if _exact_match(signals_a.get("company"), signals_b.get("company")):
        reasons.append("same_company")

    # Blog domain matches website domain
    blog_a = signals_a.get("blog_url")
    website_b = signals_b.get("website_url")
    if blog_a and website_b and _url_match(blog_a, website_b):
        reasons.append("blog_website_match")

    # LinkedIn URL contains display name from other source
    linkedin = signals_a.get("linkedin_url") or signals_b.get("linkedin_url")
    name = signals_b.get("display_name") or signals_a.get("display_name")
    if linkedin and name:
        # Extract slug from linkedin URL
        slug = linkedin.split("/in/")[-1].split("/")[0].replace("-", " ").lower()
        if (slug and name.lower() in slug) or slug in name.lower():
            reasons.append("linkedin_name_match")

    return reasons


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def match_confidence(
    observations_a: list[dict[str, object]],
    observations_b: list[dict[str, object]],
) -> tuple[float, list[str]]:
    """Compute a match confidence between two persons.

    Args:
        observations_a: Observations for person A (as dicts with
            predicate, object_value keys).
        observations_b: Observations for person B.

    Returns:
        Tuple of (confidence 0.0-1.0, list of reason strings).
    """
    signals_a = _extract_signals(observations_a)
    signals_b = _extract_signals(observations_b)
    reasons: list[str] = []

    # 1. Email exact match (strongest)
    if _exact_match(signals_a.get("email"), signals_b.get("email")):
        return 1.0, ["email_exact"]

    # 2. Twitter handle exact match
    if _exact_match(signals_a.get("twitter_handle"), signals_b.get("twitter_handle")):
        return 0.95, ["twitter_exact"]

    # 3. Blog/website URL exact match
    blog_a = signals_a.get("blog_url")
    website_b = signals_b.get("website_url")
    if blog_a and website_b and _url_match(blog_a, website_b):
        return 0.95, ["url_exact"]
    # Also check reverse: website_a vs blog_b
    website_a = signals_a.get("website_url")
    blog_b = signals_b.get("blog_url")
    if website_a and blog_b and _url_match(website_a, blog_b):
        return 0.95, ["url_exact"]

    # 4. Name similarity
    name_a = signals_a.get("display_name")
    name_b = signals_b.get("display_name")
    sim = _name_similarity(name_a, name_b)

    if sim >= 90.0:
        corroboration = _corroborating_signals(signals_a, signals_b)
        if corroboration:
            reasons = ["name_fuzzy", *corroboration]
            return 0.85, reasons
        else:
            return 0.5, ["name_fuzzy_only"]

    # 5. No match
    return 0.0, []


def should_auto_merge(confidence: float, threshold: float = 0.8) -> bool:
    """Return True if the confidence is high enough for automatic merge."""
    return confidence >= threshold
