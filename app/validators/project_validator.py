"""Validates the free-text project description length/quality. Content
safety (header injection, sensitive data, scripts) is handled by the
dedicated validators for those concerns — this module only checks that the
description is substantive enough to be useful to the team.
"""
from __future__ import annotations

from app.validators.validation_result import ValidationResult, fail, ok

MIN_LENGTH = 5
MAX_LENGTH = 2000


def validate_project_description(raw_value: str) -> ValidationResult:
    if not raw_value or not raw_value.strip():
        return fail("project_description_required", "Please tell us a bit about your project.")

    value = raw_value.strip()

    if len(value) < MIN_LENGTH:
        return fail(
            "project_description_too_short",
            "Please provide a bit more detail about your project.",
        )

    if len(value) > MAX_LENGTH:
        return fail(
            "project_description_too_long",
            f"Please keep the project description under {MAX_LENGTH} characters.",
        )

    return ok(value)
