"""Processing pipeline — reconcile observations into Claims with embeddings."""

from app.processing.dedup import deduplicate_claims
from app.processing.embeddings import embed_observations
from app.processing.reconcile import reconcile_observations

__all__ = [
    "deduplicate_claims",
    "embed_observations",
    "reconcile_observations",
]