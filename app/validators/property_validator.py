from __future__ import annotations

from app.validators.validation_result import ValidationResult, fail, ok

ALLOWED_PROPERTY_TYPES = {
    "single_family_home",
    "townhome",
    "condo",
    "multi_family",
    "commercial",
    "other",
}


def validate_property_type(raw_value: str) -> ValidationResult:
    normalized = (raw_value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if normalized not in ALLOWED_PROPERTY_TYPES:
        return fail(
            "property_type_invalid",
            "Please choose single-family home, townhome, condo, multi-family, commercial, or other.",
        )
    return ok(normalized)
