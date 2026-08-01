from __future__ import annotations

import re

from app.validators.validation_result import ValidationResult, fail, ok

_DIGITS = re.compile(r"\d")


def validate_phone(raw_value: str) -> ValidationResult:
    if not raw_value or not raw_value.strip():
        return fail("phone_required", "Please provide a phone number.")

    digits = "".join(_DIGITS.findall(raw_value))

    # Allow a leading US country code.
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    if len(digits) != 10:
        return fail("phone_invalid_length", "Please provide a 10-digit US phone number.")

    if digits[0] in ("0", "1") or digits[3] in ("0", "1"):
        return fail("phone_invalid_area_code", "That doesn't look like a valid US phone number.")

    normalized = f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    return ok(normalized)
