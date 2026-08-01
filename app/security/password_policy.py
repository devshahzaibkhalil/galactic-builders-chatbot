"""Password strength policy for admin accounts.

Customers are never asked for a password (see spec section 12) — this
module is only ever invoked from admin account creation / password change.
"""
from __future__ import annotations

import re

from app.validators.validation_result import ValidationResult, fail, ok

MIN_LENGTH = 12

_HAS_UPPER = re.compile(r"[A-Z]")
_HAS_LOWER = re.compile(r"[a-z]")
_HAS_DIGIT = re.compile(r"\d")
_HAS_SYMBOL = re.compile(r"[^A-Za-z0-9]")

_COMMON_PASSWORDS = {"password123", "letmein123", "changeme123", "qwerty123456"}


def validate_password_strength(raw_password: str) -> ValidationResult:
    if not raw_password:
        return fail("password_required", "A password is required.")

    if len(raw_password) < MIN_LENGTH:
        return fail("password_too_short", f"Password must be at least {MIN_LENGTH} characters.")

    checks = [_HAS_UPPER, _HAS_LOWER, _HAS_DIGIT, _HAS_SYMBOL]
    if sum(bool(pattern.search(raw_password)) for pattern in checks) < 3:
        return fail(
            "password_too_weak",
            "Password must include at least three of: uppercase, lowercase, digit, symbol.",
        )

    if raw_password.lower() in _COMMON_PASSWORDS:
        return fail("password_too_common", "That password is too common. Please choose another.")

    return ok(raw_password)
