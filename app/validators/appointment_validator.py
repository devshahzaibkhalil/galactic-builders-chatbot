"""Aggregates field validators for a full appointment/callback request."""
from __future__ import annotations

from typing import Any, TypedDict

from app.validators.date_time_validator import validate_appointment_date, validate_time_window
from app.validators.email_validator import validate_email
from app.validators.phone_validator import validate_phone

ALLOWED_APPOINTMENT_TYPES = {"callback", "consultation"}


class AppointmentValidationResult(TypedDict):
    valid: bool
    normalized: dict[str, Any]
    errors: dict[str, str]


def validate_appointment(payload: dict[str, Any]) -> AppointmentValidationResult:
    errors: dict[str, str] = {}
    normalized: dict[str, Any] = dict(payload)

    appointment_type = (payload.get("appointment_type") or "").strip().lower()
    if appointment_type not in ALLOWED_APPOINTMENT_TYPES:
        errors["appointment_type"] = "Please choose 'callback' or 'consultation'."
    else:
        normalized["appointment_type"] = appointment_type

    if not payload.get("phone") and not payload.get("email"):
        errors["contact"] = "A phone number or email address is required."

    if payload.get("email"):
        result = validate_email(payload["email"])
        if not result["valid"]:
            errors["email"] = result["message"] or "Invalid email."
        else:
            normalized["email"] = result["normalized_value"]

    if payload.get("phone"):
        result = validate_phone(payload["phone"])
        if not result["valid"]:
            errors["phone"] = result["message"] or "Invalid phone."
        else:
            normalized["phone"] = result["normalized_value"]

    if payload.get("requested_date"):
        result = validate_appointment_date(payload["requested_date"])
        if not result["valid"]:
            errors["requested_date"] = result["message"] or "Invalid date."
        else:
            normalized["requested_date"] = result["normalized_value"]

    if payload.get("time_window"):
        result = validate_time_window(payload["time_window"])
        if not result["valid"]:
            errors["time_window"] = result["message"] or "Invalid time window."
        else:
            normalized["time_window"] = result["normalized_value"]

    return {"valid": not errors, "normalized": normalized, "errors": errors}
