"""Aggregates individual field validators for a full lead submission.

This is the ONLY place that decides whether a complete lead payload may be
passed to lead_service.submit_lead(). Individual validators stay single-
purpose; this module just orchestrates them and collects every error so the
customer isn't stuck fixing one field at a time.
"""
from __future__ import annotations

from typing import Any, Optional, TypedDict

from app.validators.address_validator import validate_street_address
from app.validators.consent_validator import validate_contact_consent
from app.validators.email_validator import validate_email
from app.validators.header_injection_validator import validate_no_header_injection
from app.validators.location_validator import validate_city, validate_state
from app.validators.phone_validator import validate_phone
from app.validators.project_validator import validate_project_description
from app.validators.sensitive_data_validator import validate_no_sensitive_data
from app.validators.zip_validator import validate_zip


class LeadValidationResult(TypedDict):
    valid: bool
    normalized: dict[str, Any]
    errors: dict[str, str]


REQUIRED_FIELDS = ("service_key", "project_description", "email", "phone")


def validate_lead(payload: dict[str, Any], *, knowledge_service: Optional[Any] = None) -> LeadValidationResult:
    """knowledge_service is optional: when provided, service_key is checked
    against the live enabled-service catalog (see service_validator.py);
    when omitted (the default, used by lead_service.submit_lead today),
    only presence is checked, preserving existing call sites."""
    errors: dict[str, str] = {}
    normalized: dict[str, Any] = dict(payload)

    for field in REQUIRED_FIELDS:
        if not payload.get(field):
            errors[field] = f"{field.replace('_', ' ')} is required."

    if knowledge_service is not None and payload.get("service_key"):
        from app.validators.service_validator import validate_service_key
        service_result = validate_service_key(payload["service_key"], knowledge_service)
        if not service_result["valid"]:
            errors["service_key"] = service_result["message"] or "Invalid service."
        else:
            normalized["service_key"] = service_result["normalized_value"]

    email_result = validate_email(payload.get("email", ""))
    if not email_result["valid"]:
        errors["email"] = email_result["message"] or "Invalid email."
    else:
        normalized["email"] = email_result["normalized_value"]

    phone_result = validate_phone(payload.get("phone", ""))
    if not phone_result["valid"]:
        errors["phone"] = phone_result["message"] or "Invalid phone."
    else:
        normalized["phone"] = phone_result["normalized_value"]

    if payload.get("zip_code"):
        zip_result = validate_zip(payload["zip_code"])
        if not zip_result["valid"]:
            errors["zip_code"] = zip_result["message"] or "Invalid ZIP code."
        else:
            normalized["zip_code"] = zip_result["normalized_value"]

    if payload.get("city"):
        city_result = validate_city(payload["city"])
        if not city_result["valid"]:
            errors["city"] = city_result["message"] or "Invalid city."
        else:
            normalized["city"] = city_result["normalized_value"]

    if payload.get("state"):
        state_result = validate_state(payload["state"])
        if not state_result["valid"]:
            errors["state"] = state_result["message"] or "Invalid state."
        else:
            normalized["state"] = state_result["normalized_value"]

    if payload.get("street_address"):
        address_result = validate_street_address(payload["street_address"])
        if not address_result["valid"]:
            errors["street_address"] = address_result["message"] or "Invalid address."
        else:
            normalized["street_address"] = address_result["normalized_value"]

    description = payload.get("project_description")
    if description:
        length_result = validate_project_description(description)
        if not length_result["valid"]:
            errors["project_description"] = length_result["message"] or "Invalid content."
        else:
            header_result = validate_no_header_injection(description)
            if not header_result["valid"]:
                errors["project_description"] = header_result["message"] or "Invalid content."
            else:
                sensitive_result = validate_no_sensitive_data(description)
                if not sensitive_result["valid"]:
                    errors["project_description"] = sensitive_result["message"] or "Invalid content."

    if payload.get("interest_response") != "yes":
        errors["interest_response"] = (
            "Interest must be confirmed as Yes before the lead can be submitted."
        )

    consent_result = validate_contact_consent(payload.get("contact_consent_given"))
    if not consent_result["valid"]:
        errors["contact_consent_given"] = consent_result["message"] or "Consent required."

    return {"valid": not errors, "normalized": normalized, "errors": errors}
