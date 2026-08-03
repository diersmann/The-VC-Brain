"""Async MinIO / S3-compatible object storage client.

Provides put_snapshot and get_snapshot for immutable raw snapshots.
Content-addressed by SHA-256 hash for deduplication.
"""

from __future__ import annotations

import hashlib
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

S3Client = Any  # aioboto3 has no stubs


# ---------------------------------------------------------------------------
# Client lifecycle
# ---------------------------------------------------------------------------

_client: S3Client | None = None
_bucket_ensured: bool = False


async def _get_client() -> S3Client:
    """Lazy-init and return the aioboto3 S3 client singleton."""
    global _client
    if _client is not None:
        return _client

    import aioboto3  # type: ignore[import-untyped]

    from app.config import get_settings

    settings = get_settings()
    session = aioboto3.Session()
    _client = await session.client(
        "s3",
        endpoint_url=(
            f"https://{settings.minio_endpoint}"
            if settings.minio_secure
            else f"http://{settings.minio_endpoint}"
        ),
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
    ).__aenter__()

    await _ensure_bucket(_client, settings.minio_bucket)
    return _client


async def _ensure_bucket(client: S3Client, bucket: str) -> None:
    """Create the bucket if it does not exist (idempotent)."""
    global _bucket_ensured
    if _bucket_ensured:
        return
    try:
        await client.head_bucket(Bucket=bucket)
    except client.exceptions.ClientError as exc:
        if exc.response["Error"]["Code"] == "404":
            await client.create_bucket(Bucket=bucket)
            logger.info("storage_bucket_created", bucket=bucket)
        else:
            raise
    _bucket_ensured = True


async def close_client() -> None:
    """Explicitly close the S3 client (called during app shutdown)."""
    global _client, _bucket_ensured
    if _client is not None:
        await _client.__aexit__(None, None, None)
        _client = None
        _bucket_ensured = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def put_snapshot(
    content: bytes,
    content_type: str,
    source_type: str,
) -> tuple[str, str]:
    """Store raw content in MinIO, keyed by SHA-256 hash.

    Returns (content_hash_hex, storage_path).
    If the content already exists (same hash), the upload is skipped.
    """
    from app.config import get_settings

    content_hash = hashlib.sha256(content).hexdigest()
    storage_path = f"{source_type}/{content_hash}"

    client = await _get_client()
    settings = get_settings()

    try:
        await client.head_object(Bucket=settings.minio_bucket, Key=storage_path)
        logger.debug("storage_skip_duplicate", key=storage_path)
    except client.exceptions.ClientError as exc:
        if exc.response["Error"]["Code"] == "404":
            await client.put_object(
                Bucket=settings.minio_bucket,
                Key=storage_path,
                Body=content,
                ContentType=content_type,
            )
            logger.info("storage_snapshot_stored", key=storage_path, size=len(content))
        else:
            raise

    return content_hash, storage_path


async def get_snapshot(storage_path: str) -> bytes:
    """Retrieve raw content from MinIO by storage path."""
    from app.config import get_settings

    client = await _get_client()
    settings = get_settings()

    response = await client.get_object(
        Bucket=settings.minio_bucket,
        Key=storage_path,
    )
    body: bytes = await response["Body"].read()
    return body


async def check_health() -> None:
    """Verify that the configured object-storage bucket is reachable."""
    from app.config import get_settings

    client = await _get_client()
    await client.head_bucket(Bucket=get_settings().minio_bucket)
