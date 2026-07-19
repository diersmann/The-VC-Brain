"""Connector registry — maps source_type to Connector instances.

Connectors are lazy-imported to keep startup fast.  Register a new
connector by adding it to ``_BUILTIN`` and importing the module inside
``_load()``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.collectors.base import Connector

_registry: dict[str, Connector] = {}

# (source_type, module_path, class_name)
_BUILTIN: list[tuple[str, str, str]] = [
    ("github", "app.collectors.sources.github", "GitHubConnector"),
    ("producthunt", "app.collectors.sources.producthunt", "ProductHuntConnector"),
    ("arxiv", "app.collectors.sources.arxiv", "ArxivConnector"),
    ("web", "app.collectors.sources.website", "WebsiteConnector"),
    ("tavily_search", "app.collectors.sources.tavily_search", "TavilySearchConnector"),
    ("hackernews", "app.collectors.sources.hackernews", "HackerNewsConnector"),
    ("youtube", "app.collectors.sources.youtube", "YouTubeConnector"),
    ("podcasts", "app.collectors.sources.podcasts", "PodcastsConnector"),
    ("hackathons", "app.collectors.sources.hackathons", "HackathonsConnector"),
    ("linkedin", "app.collectors.sources.linkedin", "LinkedInConnector"),
]


def _load(source_type: str) -> Connector:
    """Import and instantiate a connector, caching it."""
    if source_type in _registry:
        return _registry[source_type]

    for st, mod_path, cls_name in _BUILTIN:
        if st == source_type:
            import importlib

            mod = importlib.import_module(mod_path)
            cls = getattr(mod, cls_name)
            instance: Connector = cls()
            _registry[source_type] = instance
            return instance

    msg = f"Unknown source_type: {source_type}"
    raise KeyError(msg)


def get_connector(source_type: str) -> Connector:
    """Return the connector for *source_type* (lazy-loaded and cached)."""
    return _load(source_type)


def all_connectors() -> dict[str, Connector]:
    """Return all registered connectors, loading any that haven't been loaded yet."""
    for st, _mod_path, _cls_name in _BUILTIN:
        if st not in _registry:
            _load(st)
    return dict(_registry)
