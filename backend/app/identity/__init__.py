"""Identity resolution package — detects and merges duplicate Person records.

Usage:
    from app.identity import resolve_identities
    summary = await resolve_identities(session, redis)
"""

from app.identity.matchers import match_confidence, should_auto_merge
from app.identity.merge import merge_persons
from app.identity.resolve import resolve_identities

__all__ = [
    "match_confidence",
    "merge_persons",
    "resolve_identities",
    "should_auto_merge",
]
