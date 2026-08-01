"""Flags sensitive financial/identity data (SSNs, credit card numbers)
accidentally typed into a free-text field like project_description — the
chatbot never asks for this, but a customer might paste it unprompted, and
it should never silently sail into a lead record or an email body.
"""
from __future__ import annotations

import re

from app.validators.validation_result import ValidationResult, fail, ok

_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def _luhn_valid(digits: str) -> bool:
    total = 0
    reverse_digits = digits[::-1]
    for i, ch in enumerate(reverse_digits):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def validate_no_sensitive_data(raw_value: str) -> ValidationResult:
    if not raw_value:
        return ok("")

    if _SSN_PATTERN.search(raw_value):
        return fail(
            "sensitive_data_ssn_detected",
            "Please don't include a Social Security Number here. The team will never ask for one through this chat.",
        )

    for match in _CREDIT_CARD_PATTERN.finditer(raw_value):
        digits = re.sub(r"[ -]", "", match.group(0))
        if 13 <= len(digits) <= 19 and _luhn_valid(digits):
            return fail(
                "sensitive_data_card_detected",
                "Please don't include payment card details here. The team will never ask for these through this chat.",
            )

    return ok(raw_value)
