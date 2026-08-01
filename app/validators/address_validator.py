from __future__ import annotations

import re

from app.validators.header_injection_validator import validate_no_header_injection
from app.validators.validation_result import ValidationResult, fail, ok

_HAS_DIGIT = re.compile(r"\d")
_ALLOWED_CHARS = re.compile(r"^[A-Za-z0-9.,'#\- ]{4,255}$")


def validate_street_address(raw_value: str) -> ValidationResult:
    if not raw_value or not raw_value.strip():
        return fail("address_required", "Please provide a street address.")

    value = raw_value.strip()

    header_check = validate_no_header_injection(value)
    if not header_check["valid"]:
        return fail("address_invalid_characters", "This field contains characters that are not allowed.")

    if not _ALLOWED_CHARS.fullmatch(value):
        return fail("address_invalid_characters", "Please provide a valid street address.")

    if not _HAS_DIGIT.search(value):
        return fail("address_missing_number", "Please include the house or building number.")

    return ok(" ".join(value.split()))
