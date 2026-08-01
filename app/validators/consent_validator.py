from __future__ import annotations

from app.validators.validation_result import ValidationResult, fail, ok


def validate_contact_consent(consent_given: bool | None) -> ValidationResult:
    """The lead must not be committed without explicit contact consent.

    A Yes on the interest-confirmation step is never accepted as a
    substitute for this — see app/models/lead.py LeadConsent docstring.
    """
    if consent_given is not True:
        return fail(
            "contact_consent_required",
            "Please review and accept the contact consent to submit your request.",
        )
    return ok("true")
