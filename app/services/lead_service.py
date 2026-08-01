"""Coordinates lead creation, interest confirmation, and submission.

Owns the exact ordering required by the spec:
    validate -> spam/security checks -> begin transaction -> save lead ->
    save consent -> create public reference -> create notification record ->
    commit -> queue notification email -> customer confirmation

The notification email is only ever queued through the notifier callback,
and that callback is called strictly after session.commit() succeeds — this
is enforced by construction below, not by convention.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.models.email_notification import EmailNotification
from app.models.lead import InterestResponse, Lead, LeadConsent, LeadStatus
from app.services.notification_service import notify_new_lead
from app.validators.duplicate_validator import check_duplicate
from app.validators.interest_response_validator import validate_interest_response
from app.validators.lead_validator import validate_lead
from app.validators.spam_validator import check_spam

logger = logging.getLogger("galactic.lead_service")

QueueEmailFn = Callable[[str, str], None]  # (lead_id, notification_type) -> None

INTEREST_CONFIRMATION_VERSION = "v1"


class LeadValidationError(ValueError):
    def __init__(self, errors: dict[str, str]):
        super().__init__("Lead payload failed validation.")
        self.errors = errors


class InterestNotConfirmedError(ValueError):
    """Raised if submit_lead is called before a Yes interest response is recorded."""


def record_interest_response(
    session: Session, lead: Lead, raw_response: str, *, from_button: bool = False
) -> Lead:
    """Handle the mandatory interest-confirmation step for an in-progress lead.

    Returns the same Lead with interest_* fields updated. Does not commit —
    caller controls the transaction boundary (submit_lead does, for the Yes
    path; the No path is typically committed by the caller separately since
    it does not produce a confirmed opportunity).
    """
    result = validate_interest_response(raw_response, from_button=from_button)
    if not result["valid"]:
        # Side questions or unclear text never move interest_response.
        return lead

    lead.interest_response = InterestResponse(result["normalized_value"])
    lead.interest_confirmed = result["normalized_value"] == "yes"
    lead.interest_confirmed_at = datetime.now(timezone.utc)
    lead.interest_confirmation_version = INTEREST_CONFIRMATION_VERSION

    if result["normalized_value"] == "no":
        lead.status = LeadStatus.NOT_CONFIRMED

    return lead


def _run_spam_checks(session: Session, payload: dict[str, Any]) -> Optional[str]:
    spam_result = check_spam(payload)
    if not spam_result["valid"]:
        return spam_result["error_code"]

    email = payload.get("email")
    service_key = payload.get("service_key")
    if email and service_key:
        duplicate_result = check_duplicate(session, email=email, service_key=service_key)
        if not duplicate_result["valid"]:
            return duplicate_result["error_code"]

    return None


def submit_lead(
    session: Session,
    payload: dict[str, Any],
    *,
    queue_email: QueueEmailFn,
) -> Lead:
    """Validate, persist, and queue notifications for a confirmed lead.

    Raises LeadValidationError or InterestNotConfirmedError instead of
    partially writing anything — the caller's transaction is rolled back by
    the `with session.begin()` block on any exception.
    """
    validation = validate_lead(payload)
    if not validation["valid"]:
        raise LeadValidationError(validation["errors"])

    if payload.get("interest_response") != "yes":
        raise InterestNotConfirmedError("Lead cannot be submitted before interest_response is 'yes'.")

    spam_error = _run_spam_checks(session, {**payload, "email": validation["normalized"].get("email")})
    if spam_error:
        raise LeadValidationError({"spam": spam_error})

    normalized = validation["normalized"]

    try:
        lead = Lead(
            service_key=normalized["service_key"],
            project_description=normalized["project_description"],
            city=normalized.get("city"),
            state=normalized.get("state"),
            zip_code=normalized.get("zip_code"),
            street_address=normalized.get("street_address"),
            property_type=normalized.get("property_type"),
            project_stage=normalized.get("project_stage"),
            timeline=normalized.get("timeline"),
            budget_range=normalized.get("budget_range"),
            photo_count=normalized.get("photo_count", 0),
            full_name=normalized.get("full_name"),
            email=normalized["email"],
            phone=normalized["phone"],
            preferred_contact_method=normalized.get("preferred_contact_method"),
            best_contact_time=normalized.get("best_contact_time"),
            safety_flag=bool(normalized.get("safety_flag")),
            source_page=normalized.get("source_page"),
            conversation_id=normalized.get("conversation_id"),
            interest_confirmed=True,
            interest_response=InterestResponse.YES,
            interest_confirmed_at=datetime.now(timezone.utc),
            interest_confirmation_version=INTEREST_CONFIRMATION_VERSION,
            status=LeadStatus.NEW,
        )
        session.add(lead)
        session.flush()  # assigns lead.id without ending the transaction

        consent = LeadConsent(
            lead_id=lead.id,
            contact_consent_given=True,
            marketing_consent_given=bool(normalized.get("marketing_consent_given", False)),
            consent_text_version=normalized.get("consent_text_version", "v1"),
            consented_at=datetime.now(timezone.utc),
        )
        session.add(consent)

        notification = EmailNotification(lead_id=lead.id, notification_type="admin_lead")
        session.add(notification)

        if normalized.get("send_customer_confirmation", True):
            session.add(EmailNotification(lead_id=lead.id, notification_type="customer_confirmation"))

        notify_new_lead(session, lead_id=lead.id, service_key=lead.service_key, city=lead.city)

        session.commit()
    except Exception:
        session.rollback()
        raise
    logger.info("Lead %s committed, queuing notifications", lead.public_reference)
    queue_email(lead.id, "admin_lead")
    if normalized.get("send_customer_confirmation", True):
        queue_email(lead.id, "customer_confirmation")

    return lead
