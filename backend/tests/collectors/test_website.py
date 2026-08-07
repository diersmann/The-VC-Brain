"""Tests for safe website collection boundaries."""

from types import SimpleNamespace

import pytest
from httpx import Response

from app.collectors.base import ConnectorError, Seed
from app.collectors.sources import website
from app.collectors.sources.website import _fetch_bounded_http, _validate_http_url


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.test/file",
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data",
        "http://localhost/admin",
        "http://service.localhost/admin",
        "http://service.internal/admin",
        "https://user:password@example.test/private",
    ],
)
def test_website_rejects_non_public_targets(url: str) -> None:
    with pytest.raises(ConnectorError, match="website_url_rejected"):
        _validate_http_url(url)


def test_website_accepts_public_http_url() -> None:
    assert _validate_http_url("https://example.test/path") == "https://example.test/path"


class _Stream:
    def __init__(self) -> None:
        self.response = Response(
            200,
            headers={"content-type": "text/plain"},
            request=website.httpx.Request("GET", "https://example.test"),
        )

    async def __aenter__(self) -> Response:
        return self.response

    async def __aexit__(self, *_args: object) -> None:
        return None


class _Client:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs

    async def __aenter__(self) -> "_Client":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    def stream(self, *_args: object, **_kwargs: object) -> _Stream:
        return _Stream()


@pytest.mark.asyncio
async def test_bounded_http_disables_ambient_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    client: _Client | None = None

    def make_client(**kwargs: object) -> _Client:
        nonlocal client
        client = _Client(**kwargs)
        return client

    monkeypatch.setattr(website.httpx, "AsyncClient", make_client)
    monkeypatch.setattr(website, "_validate_resolved_host", lambda _url: _noop())

    _final_url, content, _content_type, _status = await _fetch_bounded_http(
        "https://example.test", 100
    )

    assert content == b""
    assert client is not None
    assert client.kwargs["trust_env"] is False


async def _noop(_url: str | None = None) -> None:
    return None


@pytest.mark.asyncio
async def test_website_resolves_target_before_tavily(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Tavily:
        def extract(self, **_kwargs: object) -> dict[str, object]:
            return {"results": [{"raw_content": "content", "title": "Example"}]}

    resolved: list[str] = []

    async def record_resolution(url: str) -> None:
        resolved.append(url)

    connector = website.WebsiteConnector()
    monkeypatch.setattr(connector, "_get_tavily", lambda: _Tavily())
    monkeypatch.setattr(website, "_validate_resolved_host", record_resolution)

    collected = await connector.collect(Seed(source_type="web", handle="https://example.test"))

    assert collected.content == b"content"
    assert resolved == ["https://example.test"]


@pytest.mark.asyncio
async def test_website_rejects_private_dns_before_tavily(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Tavily:
        def extract(self, **_kwargs: object) -> dict[str, object]:
            raise AssertionError("Tavily must not receive a rejected target")

    async def reject_resolution(_url: str) -> None:
        raise ConnectorError(
            "website_url_rejected: hostname resolves to private or reserved address"
        )

    connector = website.WebsiteConnector()
    monkeypatch.setattr(connector, "_get_tavily", lambda: _Tavily())
    monkeypatch.setattr(website, "_validate_resolved_host", reject_resolution)

    with pytest.raises(ConnectorError, match="private or reserved"):
        await connector.collect(Seed(source_type="web", handle="https://example.test"))


@pytest.mark.asyncio
async def test_website_bounds_tavily_content_before_returning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Tavily:
        def extract(self, **_kwargs: object) -> dict[str, object]:
            return {"results": [{"raw_content": "too large", "title": "Example"}]}

    async def fallback(
        _url: str, _max_bytes: int
    ) -> tuple[str, bytes, str, int]:
        return "https://example.test", b"bounded", "text/plain", 200

    monkeypatch.setattr("app.config.get_settings", lambda: SimpleNamespace(website_max_bytes=5))
    monkeypatch.setattr(website, "_fetch_bounded_http", fallback)
    monkeypatch.setattr(website, "_validate_resolved_host", _noop)

    connector = website.WebsiteConnector()
    monkeypatch.setattr(connector, "_get_tavily", lambda: _Tavily())

    collected = await connector.collect(Seed(source_type="web", handle="https://example.test"))

    assert collected.content == b"bounded"
