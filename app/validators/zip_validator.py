from __future__ import annotations

import re

from app.validators.validation_result import ValidationResult, fail, ok

_ZIP_PATTERN = re.compile(r"^\d{5}(-\d{4})?$")


def validate_zip(raw_value: str) -> ValidationResult:
    if not raw_value or not raw_value.strip():
        return fail("zip_required", "Please provide a ZIP code.")

    value = raw_value.strip()
    if not _ZIP_PATTERN.fullmatch(value):
        return fail("zip_invalid_format", "Please provide a valid 5-digit ZIP code.")

    return ok(value[:5])
