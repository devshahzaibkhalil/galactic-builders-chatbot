from __future__ import annotations

from app.validators.validation_result import ValidationResult, fail, ok

ALLOWED_CONTACT_METHODS = {"email", "phone", "text"}


def validate_contact_method(raw_value: str) -> ValidationResult:
    normalized = (raw_value or "").strip().lower()
    if normalized not in ALLOWED_CONTACT_METHODS:
        return fail("contact_method_invalid", "Please choose email, phone, or text.")
    return ok(normalized)
