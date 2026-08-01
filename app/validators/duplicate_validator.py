"""Flags a lead submission as a likely duplicate of one already submitted
very recently for the same email + service. Does not reject outright —
returns a flag the caller can act on (e.g. still save, but mark for review)
since a customer legitimately re-submitting after fixing a typo is common.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories import lead_repository
from app.validators.validation_result import ValidationResult, fail, ok

DEFAULT_DUPLICATE_WINDOW_MINUTES = 10


def check_duplicate(
    session: Session, *, email: str, service_key: str, within_minutes: int = DEFAULT_DUPLICATE_WINDOW_MINUTES
) -> ValidationResult:
    existing = lead_repository.find_recent_by_email_and_service(
        session, email=email, service_key=service_key, within_minutes=within_minutes
    )
    if existing:
        return fail(
            "duplicate_submission",
            "It looks like you already submitted a similar request recently. "
            "The team will follow up on that request shortly.",
        )
    return ok("no_duplicate")
