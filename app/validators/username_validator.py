from __future__ import annotations

import re

from app.validators.validation_result import ValidationResult, fail, ok

_USERNAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{1,30}[a-z0-9])?$")
_RESERVED = {"admin", "root", "superadmin", "system", "support", "null", "undefined"}


def validate_username(raw_value: str) -> ValidationResult:
    if not raw_value or not raw_value.strip():
        return fail("username_required", "Please provide a username.")

    value = raw_value.strip().lower()

    if len(value) < 3:
        return fail("username_too_short", "Username must be at least 3 characters.")

    if not _USERNAME_PATTERN.fullmatch(value):
        return fail(
            "username_invalid_format",
            "Username may only contain lowercase letters, numbers, periods, underscores, and hyphens.",
        )

    if value in _RESERVED:
        return fail("username_reserved", "That username is reserved. Please choose another.")

    return ok(value)
