from __future__ import annotations

import re

from app.validators.validation_result import ValidationResult, fail, ok

_NAME_PATTERN = re.compile(r"^[A-Za-z\u00C0-\u024F' \-.]{2,120}$")
_REPEATED_CHAR = re.compile(r"(.)\1{4,}")  # e.g. "aaaaa" — spam signal, not a real name


def validate_name(raw_value: str) -> ValidationResult:
    if not raw_value or not raw_value.strip():
        return fail("name_required", "Please provide a name.")

    value = raw_value.strip()

    if len(value) < 2:
        return fail("name_too_short", "Please provide a full name.")

    if not _NAME_PATTERN.fullmatch(value):
        return fail("name_invalid_characters", "Please use only letters, spaces, hyphens, and apostrophes.")

    if _REPEATED_CHAR.search(value):
        return fail("name_looks_invalid", "That doesn't look like a valid name.")

    return ok(" ".join(value.split()))
