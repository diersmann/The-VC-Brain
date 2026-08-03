"""Quarantine and validate untrusted inbound pitch-deck uploads."""

from __future__ import annotations

import asyncio
import io
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import BinaryIO

import pypdf
from fastapi import UploadFile

from app.config import Settings


class UploadRejected(ValueError):
    """Raised when an upload fails a safety or format check."""


def _validate_filename(filename: str | None) -> str:
    if (
        not filename
        or len(filename) > 255
        or any(ord(character) < 32 or ord(character) == 127 for character in filename)
    ):
        raise UploadRejected("A safe PDF filename is required")
    if Path(filename).name != filename or "/" in filename or "\\" in filename:
        raise UploadRejected("Path components are not allowed in filenames")
    if Path(filename).suffix.lower() != ".pdf":
        raise UploadRejected("Only PDF pitch decks are supported")
    return filename


def _validate_pdf_bytes(content: bytes, *, max_pages: int) -> int:
    if not content.startswith(b"%PDF-"):
        raise UploadRejected("The upload is not a PDF")

    eof_index = content.rfind(b"%%EOF")
    if eof_index < 0 or content[eof_index + len(b"%%EOF") :].strip():
        raise UploadRejected("The upload contains trailing content")

    try:
        reader = pypdf.PdfReader(io.BytesIO(content), strict=True)
        if reader.is_encrypted:
            raise UploadRejected("Encrypted PDFs cannot be processed")
        page_count = len(reader.pages)
    except UploadRejected:
        raise
    except Exception as exc:
        raise UploadRejected("The PDF could not be parsed safely") from exc

    if page_count < 1:
        raise UploadRejected("The PDF must contain at least one page")
    if page_count > max_pages:
        raise UploadRejected(f"The PDF exceeds the {max_pages}-page limit")
    return page_count


async def _stream_to_quarantine(upload: UploadFile, destination: BinaryIO, max_bytes: int) -> int:
    total = 0
    while chunk := await upload.read(1024 * 1024):
        total += len(chunk)
        if total > max_bytes:
            raise UploadRejected(f"The upload exceeds the {max_bytes}-byte limit")
        destination.write(chunk)
    destination.flush()
    return total


async def _scan_quarantined_file(path: Path, settings: Settings) -> None:
    """Scan with a configured executable and fail closed outside development.

    The command is configured as an executable plus optional arguments and is
    invoked without a shell. The quarantine path is appended as the final
    argument, which supports commands such as ``clamscan --no-summary``.
    """
    command = settings.upload_malware_scanner.strip()
    if not command:
        if settings.environment.lower() not in {"development", "test"}:
            raise UploadRejected("Upload malware scanner is not configured")
        return

    args = [*shlex.split(command), str(path)]
    try:
        completed = await asyncio.to_thread(
            subprocess.run,
            args,
            capture_output=True,
            check=False,
            timeout=settings.upload_scan_timeout_seconds,
            text=True,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UploadRejected("Upload malware scan was unavailable") from exc

    if completed.returncode != 0:
        raise UploadRejected("The upload did not pass malware scanning")


async def quarantine_pitch_upload(upload: UploadFile, settings: Settings) -> bytes:
    """Stream, scan, and validate a pitch deck before it reaches object storage."""
    _validate_filename(upload.filename)
    if upload.content_type not in {None, "", "application/pdf", "application/octet-stream"}:
        raise UploadRejected("The upload MIME type is not supported")

    with tempfile.TemporaryDirectory(prefix="vcb-upload-") as directory:
        path = Path(directory) / "upload.pdf"
        with path.open("wb") as quarantine_file:
            await _stream_to_quarantine(upload, quarantine_file, settings.upload_max_bytes)

        await _scan_quarantined_file(path, settings)
        content = path.read_bytes()
        _validate_pdf_bytes(content, max_pages=settings.upload_max_pages)
        return content


def extract_pdf_pages(
    content: bytes, *, max_pages: int, max_text_chars: int
) -> list[tuple[str, dict[str, object]]]:
    """Extract bounded page text with stable PDF page/character locators.

    This function is intended to run in a worker thread so malformed content
    cannot block the async worker event loop.
    """
    _validate_pdf_bytes(content, max_pages=max_pages)
    reader = pypdf.PdfReader(io.BytesIO(content), strict=True)
    pages: list[tuple[str, dict[str, object]]] = []
    remaining = max_text_chars
    for page_number, page in enumerate(reader.pages, start=1):
        if remaining <= 0:
            break
        text = page.extract_text() or ""
        bounded_text = text[:remaining]
        pages.append(
            (
                bounded_text,
                {
                    "kind": "pdf",
                    "page": page_number,
                    "char_start": 0,
                    "char_end": len(bounded_text),
                },
            )
        )
        remaining -= len(bounded_text)
    return pages


def extract_pdf_text(content: bytes, *, max_pages: int, max_text_chars: int) -> str:
    """Extract bounded text from a previously validated PDF."""
    return "\n".join(
        text
        for text, _locator in extract_pdf_pages(
            content, max_pages=max_pages, max_text_chars=max_text_chars
        )
    )
