"""Tests for safe website collection boundaries."""

import pytest

from app.collectors.base import ConnectorError
from app.collectors.sources.website import _validate_http_url


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.test/file",
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data",
        "http://localhost/admin",
        "https://user:password@example.test/private",
    ],
)
def test_website_rejects_non_public_targets(url: str) -> None:
    with pytest.raises(ConnectorError, match="website_url_rejected"):
        _validate_http_url(url)


def test_website_accepts_public_http_url() -> None:
    assert _validate_http_url("https://example.test/path") == "https://example.test/path"
