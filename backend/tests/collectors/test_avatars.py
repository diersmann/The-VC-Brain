"""Tests for safe avatar source selection and metadata extraction."""

from app.collectors.avatars import parse_linkedin_meta, select_linkedin_profile_urls


def test_parse_linkedin_meta() -> None:
    title, image = parse_linkedin_meta(
        '<html><head><meta property="og:title" content="Ada Lovelace - Founder | LinkedIn">'
        '<meta content="https://media.licdn.com/avatar.jpg?a=1&amp;b=2" property="og:image">'
        "</head></html>"
    )

    assert title == "Ada Lovelace - Founder | LinkedIn"
    assert image == "https://media.licdn.com/avatar.jpg?a=1&b=2"


def test_selects_linkedin_profile_matching_verified_handle() -> None:
    result = select_linkedin_profile_urls(
        "Viet Nguyen",
        {"github": "vietnh1009"},
        [
            "https://www.linkedin.com/in/vietnguyen6",
            "https://de.linkedin.com/in/vietnh1009/",
        ],
    )

    assert result == ["https://de.linkedin.com/in/vietnh1009"]


def test_rejects_ambiguous_linkedin_profiles() -> None:
    result = select_linkedin_profile_urls(
        "Nishant Srivastava",
        {"github": "nisrulz"},
        [
            "https://www.linkedin.com/in/nishantsrivastava20",
            "https://www.linkedin.com/in/srivnis",
        ],
    )

    assert result == []
