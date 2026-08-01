"""Database operations for Lead. Owns queries only — no validation, no
business rules about what counts as a duplicate (that's
duplicate_validator.py, which calls into this).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lead import Lead


def find_recent_by_email_and_service(
    session: Session, *, email: str, service_key: str, within_minutes: int
) -> list[Lead]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=within_minutes)
    blind_index = Lead.email_lookup_index(email)
    stmt = select(Lead).where(
        Lead.email_blind_index == blind_index,
        Lead.service_key == service_key,
        Lead.created_at >= cutoff,
    )
    return list(session.execute(stmt).scalars())
