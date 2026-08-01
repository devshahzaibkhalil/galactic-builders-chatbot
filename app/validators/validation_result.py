"""Shared return shape for every field validator in app/validators/.

Every validator function returns exactly this shape so callers (chat_engine,
lead_service, schemas) never need to special-case one field's validator
against another's.
"""
from __future__ import annotations

from typing import TypedDict


class ValidationResult(TypedDict):
    valid: bool
    normalized_value: str | None
    error_code: str | None
    message: str | None


def ok(normalized_value: str) -> ValidationResult:
    return {"valid": True, "normalized_value": normalized_value, "error_code": None, "message": None}


def fail(error_code: str, message: str) -> ValidationResult:
    return {"valid": False, "normalized_value": None, "error_code": error_code, "message": message}
