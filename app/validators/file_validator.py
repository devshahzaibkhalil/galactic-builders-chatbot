"""Validates an uploaded project photo/document before storage.

This is the ONLY place file-extension/MIME/size checks happen — upload_service
calls this and nothing else re-implements the checks. Rejects extension
spoofing (a .exe renamed to .jpg) by sniffing actual file content with
libmagic rather than trusting the client-supplied filename or content-type.
"""
from __future__ import annotations

import magic

from app.validators.validation_result import ValidationResult, fail, ok

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB — mirrors MAX_UPLOAD_MB default

# extension -> set of acceptable sniffed MIME types
ALLOWED_TYPES: dict[str, set[str]] = {
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "png": {"image/png"},
    "heic": {"image/heic", "image/heif", "application/octet-stream"},
    "pdf": {"application/pdf"},
}

_DANGEROUS_MIME_MARKERS = (
    "text/x-php", "application/x-php", "application/x-msdownload",
    "application/x-executable", "text/x-shellscript", "application/x-sh",
    "text/html", "application/javascript", "text/javascript",
)


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_upload(filename: str, file_bytes: bytes) -> ValidationResult:
    if not filename or not filename.strip():
        return fail("filename_required", "A filename is required.")

    if len(file_bytes) == 0:
        return fail("file_empty", "The uploaded file is empty.")

    if len(file_bytes) > MAX_FILE_BYTES:
        return fail("file_too_large", f"Files must be under {MAX_FILE_BYTES // (1024 * 1024)} MB.")

    ext = _extension(filename)
    if ext not in ALLOWED_TYPES:
        return fail(
            "extension_not_allowed",
            "That file type isn't supported. Please upload a JPG, PNG, HEIC, or PDF.",
        )

    sniffed_mime = magic.from_buffer(file_bytes[:4096], mime=True)

    if sniffed_mime in _DANGEROUS_MIME_MARKERS:
        return fail("dangerous_content_detected", "This file could not be accepted for security reasons.")

    if sniffed_mime not in ALLOWED_TYPES[ext]:
        return fail(
            "mime_type_mismatch",
            "The file's content doesn't match its extension. Please re-upload the original file.",
        )

    return ok(sniffed_mime)
