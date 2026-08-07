"""Provider-free discovery failure and empty-page contract coverage."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.collectors.base import ConnectorError, classify_connector_failure
from app.collectors.sources.arxiv import ArxivConnector
from app.collectors.sources.github import GitHubConnector
from app.collectors.sources.hackathons import HackathonsConnector
from app.collectors.sources.linkedin import LinkedInConnector
from app.collectors.sources.podcasts import PodcastsConnector
from app.collectors.sources.producthunt import ProductHuntConnector
from app.collectors.sources.tavily_search import TavilySearchConnector
from app.collectors.sources.youtube import YouTubeConnector


@pytest.mark.parametrize(
    ("connector", "url", "status", "message"),
    [
        (GitHubConnector(), "https://api.github.com/search/users", 404, "HTTP 404"),
        (ArxivConnector(), "https://export.arxiv.org/api/query", 503, "HTTP 503"),
        (YouTubeConnector(), "https://www.googleapis.com/youtube/v3/search", 400, "HTTP 400"),
    ],
)
@pytest.mark.asyncio
async def test_http_discovery_failures_are_typed(
    connector: object,
    url: str,
    status: int,
    message: str,
) -> None:
    if isinstance(connector, YouTubeConnector):
        connector._api_key = "fixture-key"
    with respx.mock:
        respx.get(url).respond(status_code=status)
        with pytest.raises(ConnectorError, match=message) as failure:
            await connector.discover("fixture query")  # type: ignore[attr-defined]

    assert failure.value.failure_kind == ("transient" if status >= 500 else "permanent")
    assert failure.value.retryable is (status >= 500)


@pytest.mark.asyncio
async def test_producthunt_graphql_provider_error_is_not_an_empty_page() -> None:
    with respx.mock:
        respx.post("https://api.producthunt.com/v2/api/graphql").respond(
            json={"errors": [{"message": "provider unavailable"}]}
        )
        with pytest.raises(ConnectorError, match="graphql_failed"):
            await ProductHuntConnector().discover("fixture query")


@pytest.mark.parametrize(
    "connector_type",
    [TavilySearchConnector, LinkedInConnector, PodcastsConnector, HackathonsConnector],
)
@pytest.mark.asyncio
async def test_tavily_provider_exception_is_typed_for_every_registered_wrapper(
    connector_type: type[object],
) -> None:
    class FailingTavily:
        def search(self, **_kwargs: object) -> dict[str, object]:
            raise RuntimeError("provider exploded")

    connector = connector_type()
    tavily = FailingTavily()
    if isinstance(connector, TavilySearchConnector):
        connector._get_client = lambda: tavily  # type: ignore[method-assign]
    else:
        connector._get_tavily = lambda: tavily  # type: ignore[method-assign]

    with pytest.raises(ConnectorError, match="search_failed") as failure:
        await connector.discover("fixture query")  # type: ignore[attr-defined]
    assert failure.value.failure_kind == "permanent"
    assert failure.value.retryable is False


@pytest.mark.asyncio
async def test_rate_limit_provider_exception_is_retryable() -> None:
    class RateLimitedTavily:
        def search(self, **_kwargs: object) -> dict[str, object]:
            raise RuntimeError("HTTP 429 rate limit")

    connector = TavilySearchConnector()
    connector._get_client = lambda: RateLimitedTavily()  # type: ignore[method-assign]

    with pytest.raises(ConnectorError) as failure:
        await connector.discover("fixture query")
    assert classify_connector_failure(failure.value) == ("rate_limited", True)


@pytest.mark.asyncio
async def test_successful_empty_http_page_remains_empty() -> None:
    with respx.mock:
        respx.get("https://api.github.com/search/users").respond(json={"items": []})
        assert await GitHubConnector().discover("fixture query") == []

    youtube = YouTubeConnector()
    youtube._api_key = "fixture-key"
    with respx.mock:
        respx.get("https://www.googleapis.com/youtube/v3/search").respond(json={"items": []})
        assert await youtube.discover("fixture query") == []


@pytest.mark.asyncio
async def test_malformed_success_payload_is_not_an_empty_page() -> None:
    with respx.mock:
        respx.get("https://api.github.com/search/users").respond(json={})
        with pytest.raises(ConnectorError, match="missing items"):
            await GitHubConnector().discover("fixture query")

    class MalformedTavily:
        def search(self, **_kwargs: object) -> dict[str, object]:
            return {}

    connector = TavilySearchConnector()
    connector._get_client = lambda: MalformedTavily()  # type: ignore[method-assign]
    with pytest.raises(ConnectorError, match="invalid provider response"):
        await connector.discover("fixture query")


def test_network_exceptions_are_retryable_without_provider_credentials() -> None:
    assert classify_connector_failure(httpx.ReadTimeout("fixture timeout")) == (
        "transient",
        True,
    )
    assert classify_connector_failure(httpx.ConnectError("fixture connect")) == (
        "transient",
        True,
    )
    assert classify_connector_failure(httpx.RemoteProtocolError("Server disconnected")) == (
        "transient",
        True,
    )
    assert classify_connector_failure(OSError("Network is unreachable")) == (
        "transient",
        True,
    )
    assert classify_connector_failure(RuntimeError("candidate 4291")) == (
        "permanent",
        False,
    )
    assert classify_connector_failure(RuntimeError("user 500 found")) == (
        "permanent",
        False,
    )
