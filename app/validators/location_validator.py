"""Validates city and state text fields, distinct from zip_validator.py.
Cross-checking a validated city/state against the approved service area is
service_area_service.py's job, not this module's — this only validates
that the text itself is well-formed.
"""
from __future__ import annotations

import re

from app.validators.validation_result import ValidationResult, fail, ok

_CITY_PATTERN = re.compile(r"^[A-Za-z\u00C0-\u024F' \-.]{2,100}$")

_US_STATE_ABBREVIATIONS = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN",
    "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV",
    "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN",
    "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
}


def validate_city(raw_value: str) -> ValidationResult:
    if not raw_value or not raw_value.strip():
        return fail("city_required", "Please provide a city.")

    value = raw_value.strip()
    if not _CITY_PATTERN.fullmatch(value):
        return fail("city_invalid_characters", "Please provide a valid city name.")

    return ok(" ".join(value.split()))


def validate_state(raw_value: str) -> ValidationResult:
    if not raw_value or not raw_value.strip():
        return fail("state_required", "Please provide a state.")

    value = raw_value.strip().upper()
    if value not in _US_STATE_ABBREVIATIONS:
        return fail("state_invalid", "Please provide a valid two-letter US state abbreviation.")

    return ok(value)
