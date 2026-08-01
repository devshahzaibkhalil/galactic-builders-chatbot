from __future__ import annotations

from urllib.parse import urlparse

from app.validators.validation_result import ValidationResult, fail, ok

_ALLOWED_SCHEMES = {"http", "https"}


def validate_url(raw_value: str) -> ValidationResult:
    if not raw_value or not raw_value.strip():
        return fail("url_required", "Please provide a URL.")

    value = raw_value.strip()
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"

    parsed = urlparse(value)

    if parsed.scheme not in _ALLOWED_SCHEMES:
        return fail("url_invalid_scheme", "Please provide a valid http or https URL.")

    if not parsed.netloc or "." not in parsed.netloc:
        return fail("url_invalid_format", "Please provide a valid website URL.")

    if any(c in parsed.netloc for c in (" ", "<", ">", '"')):
        return fail("url_invalid_format", "Please provide a valid website URL.")

    return ok(value)
