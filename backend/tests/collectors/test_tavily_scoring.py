from app.collectors.base import Seed, classify_connector_failure
from app.collectors.jobs import _collection_source_for_seed, _rating, score_research_axis


def test_tavily_url_seeds_route_to_web_and_entity_leads_are_not_collected() -> None:
    url_seed = Seed(source_type="web", handle="https://example.test/profile")
    entity_seed = Seed(source_type="tavily_entity", handle="Ada Founder")

    assert _collection_source_for_seed("tavily_search", url_seed) == "web"
    assert _collection_source_for_seed("tavily_search", entity_seed) is None


def test_connector_failures_are_classified_for_retry() -> None:
    assert classify_connector_failure(RuntimeError("HTTP 429 rate limit")) == (
        "rate_limited",
        True,
    )
    assert classify_connector_failure(TimeoutError("request timed out")) == (
        "transient",
        True,
    )
    assert classify_connector_failure(RuntimeError("404 user not found")) == (
        "permanent",
        False,
    )


def test_research_axis_without_results_is_low_confidence() -> None:
    result = score_research_axis("founder", {"results": [], "answer": ""}, ["Ada Founder"])

    assert result["score"] == 0.5
    assert result["confidence"] == 0.0
    assert result["result_count"] == 0.0
    assert _rating(result["score"]) == "Neutral"


def test_positive_source_backed_evidence_scores_above_negative_case() -> None:
    positive = {
        "answer": (
            "Ada Founder founded and scaled Acme, launched an open source product and led the team."
        ),
        "results": [
            {
                "title": "Ada Founder profile",
                "content": "Founder who built and launched Acme",
                "url": "https://one.example/a",
                "score": 0.92,
            },
            {
                "title": "Acme history",
                "content": "Ada Founder led and scaled the company",
                "url": "https://two.example/b",
                "score": 0.85,
            },
            {
                "title": "Open source award",
                "content": "Ada Founder received an award",
                "url": "https://three.example/c",
                "score": 0.78,
            },
        ],
    }
    negative = {
        "answer": "The search found a lawsuit and misconduct controversy.",
        "results": [
            {
                "title": "Controversy",
                "content": "fraud lawsuit misconduct",
                "url": "https://one.example/a",
                "score": 0.75,
            },
        ],
    }

    positive_score = score_research_axis("founder", positive, ["Ada Founder", "Acme"])
    negative_score = score_research_axis("founder", negative, ["Ada Founder", "Acme"])

    assert positive_score["score"] > negative_score["score"]
    assert positive_score["confidence"] > negative_score["confidence"]
