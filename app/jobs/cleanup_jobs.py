"""Applies the retention policy from .env.example (LEAD_RETENTION_DAYS,
CONVERSATION_RETENTION_DAYS, FAILED_UPLOAD_RETENTION_DAYS) — those env vars
existed from the very first phase but nothing ever read them until now.

Meant to be invoked by a scheduled worker (Redis/RQ, a later phase); each
function here is a single, independently-callable unit of cleanup so a
scheduler can run them on whatever cadence makes sense, and so each is
trivially testable without a scheduler existing yet.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.email_notification import EmailNotification, NotificationStatus
from app.models.lead import Lead
from app.models.uploaded_file import UploadedFile
from app.services.storage_service import StorageService


def soft_delete_expired_leads(session: Session, *, retention_days: int, now: Optional[datetime] = None) -> int:
    """Soft-deletes (sets deleted_at) leads older than the retention
    window. Never hard-deletes — that's a separate, explicit operation an
    admin would run, not an automatic job."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=retention_days)
    stmt = select(Lead).where(Lead.created_at < cutoff, Lead.deleted_at.is_(None))
    leads = list(session.execute(stmt).scalars())
    for lead in leads:
        lead.deleted_at = now
    return len(leads)


def purge_expired_uploaded_files(
    session: Session, storage: StorageService, *, now: Optional[datetime] = None
) -> int:
    """Deletes the physical file AND marks the DB record for uploads past
    their expires_at. Runs the storage delete first — if it fails, the DB
    record stays so the job can retry, rather than losing track of an
    orphaned file on disk."""
    now = now or datetime.now(timezone.utc)
    stmt = select(UploadedFile).where(UploadedFile.expires_at < now, UploadedFile.deleted_at.is_(None))
    files = list(session.execute(stmt).scalars())
    purged = 0
    for file_record in files:
        storage.delete(file_record.storage_name)
        file_record.deleted_at = now
        purged += 1
    return purged


def purge_failed_upload_attempts(session: Session, *, retention_days: int, now: Optional[datetime] = None) -> int:
    """FAILED_UPLOAD_RETENTION_DAYS is intentionally short (default 7 days)
    — these are validation-rejected attempts, not accepted files, so there
    is nothing useful to keep long-term."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=retention_days)
    stmt = select(UploadedFile).where(
        UploadedFile.created_at < cutoff,
        UploadedFile.deleted_at.is_(None),
    )
    files = list(session.execute(stmt).scalars())
    for file_record in files:
        file_record.deleted_at = now
    return len(files)


def purge_old_email_notification_records(
    session: Session, *, retention_days: int, now: Optional[datetime] = None
) -> int:
    """Only ever purges terminal-state (SENT/FAILED) notification rows —
    never a PENDING or RETRYING one, regardless of age, since that would
    silently cancel an email still in flight."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=retention_days)
    stmt = select(EmailNotification).where(
        EmailNotification.created_at < cutoff,
        EmailNotification.status.in_([NotificationStatus.SENT, NotificationStatus.FAILED]),
    )
    records = list(session.execute(stmt).scalars())
    for record in records:
        session.delete(record)
    return len(records)
