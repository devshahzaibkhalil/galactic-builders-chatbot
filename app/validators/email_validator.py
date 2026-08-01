from __future__ import annotations

import re

from app.validators.validation_result import ValidationResult, fail, ok

_EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_HEADER_INJECTION_CHARS = re.compile(r"[\r\n]")


def validate_email(raw_value: str) -> ValidationResult:
    if not raw_value or not raw_value.strip():
        return fail("email_required", "Please provide an email address.")

    value = raw_value.strip()

    if _HEADER_INJECTION_CHARS.search(value):
        return fail("email_header_injection", "That email address contains invalid characters.")

    if len(value) > 254:
        return fail("email_too_long", "That email address is too long.")

    if not _EMAIL_PATTERN.fullmatch(value):
        return fail("email_invalid_format", "Please provide a valid email address, like name@example.com.")

    return ok(value.lower())
