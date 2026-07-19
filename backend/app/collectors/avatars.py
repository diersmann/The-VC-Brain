"""Candidate avatar collection with LinkedIn-first, GitHub fallback behavior."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Observation, Person, SourceSnapshot

logger = structlog.get_logger(__name__)

_USER_AGENT = "The-VC-Brain/0.1 (+https://github.com/diersmann/The-VC-Brain)"
_MAX_IMAGE_BYTES = 1_000_000
_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@dataclass(frozen=True)
class AvatarPayload:
    data: bytes
    mime_type: str
    sha256: str
    source_type: str
    source_url: str
    image_url: str


class _MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        values = {key.lower(): value or "" for key, value in attrs}
        key = values.get("property") or values.get("name")
        content = values.get("content", "").strip()
        if key and content:
            self.values.setdefault(key.lower(), content)


def _normalize(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value.lower()))


def select_linkedin_profile_urls(
    display_name: str,
    handles: dict[str, str] | None,
    urls: list[str],
) -> list[str]:
    """Return unambiguous public LinkedIn profile candidates in priority order."""
    unique: list[str] = []
    for url in urls:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if not host.lower().endswith("linkedin.com") or "/in/" not in parsed.path:
            continue
        normalized_url = f"{parsed.scheme or 'https'}://{parsed.netloc}{parsed.path}".rstrip("/")
        if normalized_url not in unique:
            unique.append(normalized_url)

    if len(unique) <= 1:
        return unique

    normalized_handles = {
        _normalize(handle).replace(" ", "") for handle in (handles or {}).values() if handle
    }
    handle_matches = [
        url
        for url in unique
        if _normalize(urlparse(url).path.rsplit("/", 1)[-1]).replace(" ", "") in normalized_handles
    ]
    if len(handle_matches) == 1:
        return handle_matches

    # Multiple profiles with the same common name are not safe to choose
    # automatically. GitHub is a verified handle-based fallback.
    logger.info(
        "linkedin_avatar_ambiguous",
        display_name=display_name,
        candidate_count=len(unique),
    )
    return []


def parse_linkedin_meta(html: str) -> tuple[str | None, str | None]:
    parser = _MetaParser()
    parser.feed(html)
    return parser.values.get("og:title"), parser.values.get("og:image")


async def _download_image(client: httpx.AsyncClient, image_url: str) -> tuple[bytes, str] | None:
    host = (urlparse(image_url).hostname or "").lower()
    allowed = host.endswith("licdn.com") or host.endswith("githubusercontent.com")
    if not allowed:
        logger.warning("avatar_image_host_rejected", host=host)
        return None

    response = await client.get(image_url)
    if response.status_code != 200:
        return None
    mime_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if mime_type not in _IMAGE_TYPES or not response.content:
        return None
    if len(response.content) > _MAX_IMAGE_BYTES:
        logger.warning("avatar_image_too_large", bytes=len(response.content))
        return None
    return response.content, mime_type


async def _linkedin_avatar(
    client: httpx.AsyncClient,
    person: Person,
    profile_urls: list[str],
) -> AvatarPayload | None:
    for profile_url in profile_urls:
        response = await client.get(profile_url)
        if response.status_code != 200:
            continue
        title, image_url = parse_linkedin_meta(response.text)
        if not title or not image_url:
            continue
        normalized_name = _normalize(person.display_name or "")
        if not normalized_name or normalized_name not in _normalize(title):
            logger.info("linkedin_avatar_identity_mismatch", person_id=str(person.id))
            continue
        downloaded = await _download_image(client, image_url)
        if downloaded is None:
            continue
        data, mime_type = downloaded
        return AvatarPayload(
            data=data,
            mime_type=mime_type,
            sha256=hashlib.sha256(data).hexdigest(),
            source_type="linkedin",
            source_url=profile_url,
            image_url=image_url,
        )
    return None


async def _github_avatar(
    client: httpx.AsyncClient,
    person: Person,
    github_token: str,
) -> AvatarPayload | None:
    handle = (person.handles or {}).get("github")
    if not handle:
        return None
    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    profile_url = f"https://github.com/{handle}"
    response = await client.get(f"https://api.github.com/users/{handle}", headers=headers)
    if response.status_code != 200:
        return None
    image_url = str(response.json().get("avatar_url", "")).strip()
    if not image_url:
        return None
    image_url = f"{image_url}{'&' if '?' in image_url else '?'}s=200"
    downloaded = await _download_image(client, image_url)
    if downloaded is None:
        return None
    data, mime_type = downloaded
    return AvatarPayload(
        data=data,
        mime_type=mime_type,
        sha256=hashlib.sha256(data).hexdigest(),
        source_type="github",
        source_url=profile_url,
        image_url=image_url,
    )


async def fetch_and_store_avatar(
    session: AsyncSession,
    person: Person,
    github_token: str = "",
) -> AvatarPayload | None:
    """Fetch a verified public avatar and cache its bytes on the Person row."""
    linkedin_result = await session.execute(
        select(SourceSnapshot.uri)
        .join(Observation, Observation.snapshot_id == SourceSnapshot.id)
        .where(
            Observation.subject_id == person.id,
            SourceSnapshot.uri.ilike("%linkedin.com/in/%"),
        )
        .distinct()
    )
    linkedin_urls = select_linkedin_profile_urls(
        person.display_name or "",
        person.handles,
        list(linkedin_result.scalars().all()),
    )

    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(
        headers={"User-Agent": _USER_AGENT},
        follow_redirects=True,
        timeout=timeout,
    ) as client:
        avatar = await _linkedin_avatar(client, person, linkedin_urls)
        if avatar is None:
            avatar = await _github_avatar(client, person, github_token)

    if avatar is None:
        return None

    person.avatar_data = avatar.data
    person.avatar_mime_type = avatar.mime_type
    person.avatar_sha256 = avatar.sha256
    person.avatar_source_type = avatar.source_type
    person.avatar_source_url = avatar.source_url
    person.avatar_image_url = avatar.image_url
    person.avatar_fetched_at = datetime.now(UTC)
    await session.flush()
    return avatar
