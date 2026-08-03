"""Tests for Product Hunt topic filtering and cursor pagination."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.collectors.sources.producthunt import ProductHuntConnector


def _page(
    post_id: str,
    username: str,
    *,
    end_cursor: str | None,
    has_next: bool,
) -> dict[str, object]:
    return {
        "data": {
            "posts": {
                "edges": [
                    {
                        "node": {
                            "id": post_id,
                            "name": post_id,
                            "makers": [{"username": username, "name": username}],
                        }
                    }
                ],
                "pageInfo": {"endCursor": end_cursor, "hasNextPage": has_next},
            }
        }
    }


@pytest.mark.asyncio
async def test_discover_uses_topic_and_follows_page_info_cursor() -> None:
    connector = ProductHuntConnector()
    requests: list[dict[str, object]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        after = body["variables"]["after"]
        return httpx.Response(
            200,
            json=_page(
                "post-one" if after is None else "post-two",
                "maker-one" if after is None else "maker-two",
                end_cursor="cursor-one" if after is None else None,
                has_next=after is None,
            ),
        )

    with respx.mock:
        respx.post("https://api.producthunt.com/v2/api/graphql").mock(side_effect=respond)

        seeds = await connector.discover("ai infrastructure", page=2)

    assert [seed.handle for seed in seeds] == ["maker-two"]
    assert len(requests) == 2
    assert requests[0]["variables"] == {"topic": "ai infrastructure", "first": 20, "after": None}
    assert requests[1]["variables"] == {
        "topic": "ai infrastructure",
        "first": 20,
        "after": "cursor-one",
    }
    assert "posts(topic: $topic" in requests[0]["query"]


@pytest.mark.asyncio
async def test_discover_rejects_invalid_page() -> None:
    with pytest.raises(ValueError, match="page must be at least 1"):
        await ProductHuntConnector().discover("ai", page=0)
