"""Async MinIO / S3-compatible object storage client.

Provides put_snapshot and get_snapshot for immutable raw snapshots.
Content-addressed by SHA-256 hash for deduplication.
"""

from __future__ import annotations

import asyncio
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
_lifecycle_lock = asyncio.Lock()
_closing = False
_close_finished: asyncio.Event | None = None


async def _get_client() -> S3Client:
    """Lazy-init and return the aioboto3 S3 client singleton."""
    global _client

    import aioboto3  # type: ignore[import-untyped]

    from app.config import get_settings

    settings = get_settings()

    async with _lifecycle_lock:
        if _closing:
            raise RuntimeError("storage client is closing")
        if _client is not None:
            return _client

        session = aioboto3.Session()
        client_context = session.client(
            "s3",
            endpoint_url=(
                f"https://{settings.minio_endpoint}"
                if settings.minio_secure
                else f"http://{settings.minio_endpoint}"
            ),
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
        )
        entered_client: S3Client | None = None
        try:
            entered_client = await client_context.__aenter__()
            await _ensure_bucket(entered_client, settings.minio_bucket)
        except BaseException:
            # The singleton is published only after bucket setup succeeds. If
            # setup fails, release the entered context so a retry cannot leak
            # a socket or leave a half-initialized client behind.
            if entered_client is not None:
                try:
                    await client_context.__aexit__(None, None, None)
                except BaseException:  # pragma: no cover - provider-specific cleanup failure
                    logger.warning("storage_client_init_close_failed")
            raise

        _client = entered_client
        return entered_client


async def _ensure_bucket(client: S3Client, bucket: str) -> None:
    """Create the bucket if it does not exist (idempotent)."""
    global _bucket_ensured
    if _bucket_ensured:
        return
    try:
        await client.head_bucket(Bucket=bucket)
    except client.exceptions.ClientError as exc:
        code = str(exc.response["Error"].get("Code", ""))
        if code not in {"404", "NoSuchBucket", "NotFound"}:
            raise
        try:
            await client.create_bucket(Bucket=bucket)
            logger.info("storage_bucket_created", bucket=bucket)
        except client.exceptions.ClientError as create_exc:
            # Multiple API/worker processes for the same account may observe
            # a missing bucket at the same time. S3 reports the losing create
            # as this same-owner conflict, so the bucket is ready. Do not
            # swallow generic 409/BucketAlreadyExists responses: those may
            # indicate a bucket owned by a different account.
            create_code = str(create_exc.response["Error"].get("Code", ""))
            if create_code != "BucketAlreadyOwnedByYou":
                raise
            logger.debug("storage_bucket_already_exists", bucket=bucket)
    _bucket_ensured = True


async def close_client() -> None:
    """Explicitly close the S3 client after request/worker work has quiesced."""
    global _client, _bucket_ensured, _closing, _close_finished

    async with _lifecycle_lock:
        if _closing:
            finished = _close_finished
            owner = False
            client: S3Client | None = None
            bucket_ensured = False
        else:
            _closing = True
            finished = asyncio.Event()
            _close_finished = finished
            owner = True
            client = _client
            bucket_ensured = _bucket_ensured
            _client = None
            _bucket_ensured = False

    if not owner:
        if finished is not None:
            await finished.wait()
        return

    first_error: BaseException | None = None
    try:
        if client is not None:
            await client.__aexit__(None, None, None)
    except BaseException as exc:  # pragma: no cover - provider-specific failure
        first_error = exc
        logger.warning("storage_client_close_failed", client_type=type(client).__name__)
    finally:
        async with _lifecycle_lock:
            # Keep a failed context owned by this process so the next shutdown
            # attempt can retry cleanup, matching the other client registries.
            if first_error is not None and client is not None:
                _client = client
                _bucket_ensured = bucket_ensured
            _closing = False
            if finished is not None:
                finished.set()
            _close_finished = None

    if first_error is not None:
        raise first_error


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
