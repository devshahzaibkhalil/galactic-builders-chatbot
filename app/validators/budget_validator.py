"""Validates the customer's selected budget range.

Deliberately closed to a fixed set of bucketed options (never free text) so
the estimate flow can't be tricked into carrying an unverified numeric
figure forward — pricing itself is always handled per spec §18, not here.
"""
from __future__ import annotations

from app.validators.validation_result import ValidationResult, fail, ok

ALLOWED_BUDGET_RANGES = {
    "under_5000",
    "5000_10000",
    "10000_25000",
    "25000_50000",
    "50000_plus",
    "not_sure_yet",
}


def validate_budget_range(raw_value: str) -> ValidationResult:
    normalized = (raw_value or "").strip().lower().replace(" ", "_").replace("-", "_").replace("$", "")
    if normalized not in ALLOWED_BUDGET_RANGES:
        return fail(
            "budget_range_invalid",
            "Please choose one of the available budget ranges.",
        )
    return ok(normalized)
