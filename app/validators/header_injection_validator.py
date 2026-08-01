"""Detects header-injection attempts (CRLF sequences, or raw header-like
lines) in any free-text field that might eventually be interpolated into
an email header or subject line — not just the email address itself
(email_validator.py already covers that field specifically).
"""
from __future__ import annotations

import re

from app.validators.validation_result import ValidationResult, fail, ok

_CRLF_PATTERN = re.compile(r"[\r\n]")
_HEADER_LIKE_PATTERN = re.compile(r"(?im)^(to|from|cc|bcc|subject|content-type)\s*:")


def validate_no_header_injection(raw_value: str) -> ValidationResult:
    if raw_value is None:
        return ok("")

    if _CRLF_PATTERN.search(raw_value):
        return fail("header_injection_detected", "This field contains characters that are not allowed.")

    if _HEADER_LIKE_PATTERN.search(raw_value):
        return fail("header_injection_detected", "This field contains characters that are not allowed.")

    return ok(raw_value)
