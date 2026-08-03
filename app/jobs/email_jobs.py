"""Implements the lead-email retry policy:

    Attempt 1: immediately
    Attempt 2: after 2 minutes
    Attempt 3: after 10 minutes
    Final attempt: after 30 minutes

The lead itself is never affected by email failures — this module only
ever touches EmailNotification rows. No real scheduler is wired up yet
(that's Redis/RQ, a later phase); attempt_notification() is meant to be
called by whatever scheduler eventually exists, driven by
next_retry_at()/is_due().
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.models.email_notification import EmailNotification, NotificationStatus

logger = logging.getLogger("galactic.email_jobs")

RETRY_DELAYS: list[timedelta] = [
    timedelta(seconds=0),   # attempt 1 (immediate)
    timedelta(minutes=2),   # attempt 2
    timedelta(minutes=10),  # attempt 3
    timedelta(minutes=30),  # attempt 4 (final)
]
MAX_ATTEMPTS = len(RETRY_DELAYS)

SendFn = Callable[[EmailNotification], None]  # raises on failure, returns normally on success


def next_retry_delay(attempt_count: int) -> timedelta | None:
    """attempt_count is the number of attempts already made (0 before any
    attempt). Returns the delay before the *next* attempt, or None if the
    retry budget is exhausted."""
    if attempt_count >= MAX_ATTEMPTS:
        return None
    return RETRY_DELAYS[attempt_count]


def attempt_notification(session: Session, notification: EmailNotification, send: SendFn) -> NotificationStatus:
    """Runs one send attempt and updates the notification row accordingly.

    Never raises — failures are recorded on the row so a scheduler can
    retry later, and the lead record is completely untouched either way.
    """
    notification.attempt_count += 1
    notification.last_attempted_at = datetime.now(timezone.utc)

    try:
        send(notification)
    except Exception:
        # Log with the traceback. Without this the failure reason was lost
        # entirely: the row recorded only RETRYING/FAILED, so a missing
        # recipient or a rejected sender looked identical to no email at all.
        exhausted = notification.attempt_count >= MAX_ATTEMPTS
        logger.exception(
            "Email notification %s (%s) for lead %s failed on attempt %s/%s - marking %s",
            notification.id,
            notification.notification_type,
            notification.lead_id,
            notification.attempt_count,
            MAX_ATTEMPTS,
            "FAILED" if exhausted else "RETRYING",
        )
        notification.status = NotificationStatus.FAILED if exhausted else NotificationStatus.RETRYING
        session.add(notification)
        return notification.status

    logger.info(
        "Email notification %s (%s) for lead %s sent on attempt %s",
        notification.id, notification.notification_type, notification.lead_id,
        notification.attempt_count,
    )
    notification.status = NotificationStatus.SENT
    session.add(notification)
    return notification.status
