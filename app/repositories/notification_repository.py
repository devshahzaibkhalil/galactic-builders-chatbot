from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin_notification import AdminNotification


def insert(session: Session, notification: AdminNotification) -> AdminNotification:
    session.add(notification)
    session.flush()
    return notification


def list_for_admin(
    session: Session, *, admin_id: str, unread_only: bool = True, limit: int = 50
) -> list[AdminNotification]:
    """Returns notifications targeted at this admin PLUS broadcast ones
    (recipient_admin_id is NULL), since a broadcast is meant for everyone."""
    stmt = select(AdminNotification).where(
        (AdminNotification.recipient_admin_id == admin_id) | (AdminNotification.recipient_admin_id.is_(None))
    )
    if unread_only:
        stmt = stmt.where(AdminNotification.read.is_(False))
    stmt = stmt.order_by(AdminNotification.created_at.desc()).limit(limit)
    return list(session.execute(stmt).scalars())


def get(session: Session, notification_id: str) -> AdminNotification | None:
    return session.get(AdminNotification, notification_id)
