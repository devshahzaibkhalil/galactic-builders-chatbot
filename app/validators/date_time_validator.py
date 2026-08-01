"""Validates an appointment/callback request date and time window.

Rejects past dates and unreasonably-far-future dates; does not validate
business-hours logic (that's contact_window_service.py's job — this module
only checks the date/time itself is well-formed and sane).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from app.validators.validation_result import ValidationResult, fail, ok

MAX_DAYS_IN_FUTURE = 90

ALLOWED_TIME_WINDOWS = {"morning", "afternoon", "evening", "any_time"}


def validate_appointment_date(raw_date: str, *, today: date | None = None) -> ValidationResult:
    today = today or date.today()
    try:
        parsed = datetime.strptime(raw_date.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return fail("date_invalid_format", "Please provide a date in YYYY-MM-DD format.")

    if parsed < today:
        return fail("date_in_past", "Please choose a date that hasn't already passed.")

    if parsed > today + timedelta(days=MAX_DAYS_IN_FUTURE):
        return fail("date_too_far_out", f"Please choose a date within the next {MAX_DAYS_IN_FUTURE} days.")

    return ok(parsed.isoformat())


def validate_time_window(raw_window: str) -> ValidationResult:
    normalized = (raw_window or "").strip().lower().replace(" ", "_")
    if normalized not in ALLOWED_TIME_WINDOWS:
        return fail(
            "time_window_invalid",
            "Please choose morning, afternoon, evening, or any time.",
        )
    return ok(normalized)
