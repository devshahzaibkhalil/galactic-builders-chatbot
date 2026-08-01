"""Creates and manages the admin dashboard's internal notifications (the
bell icon): new conversation, new lead, appointment booked, and unanswered
questions. Notifications are always stored in SQLite and shown via the
bell icon - that part requires no configuration.

An optional email copy is sent through app/services/smtp_transport.py if
SMTP_HOST is configured in the environment; if it isn't, notifications
still work normally and no email is attempted. No email credentials are
required unless the admin explicitly sets them.
"""
from __future__ import annotations

import os
from typing import Optional

from sqlalchemy.orm import Session

from app.models.admin_notification import AdminNotification
from app.models.admin_user import AdminUser
from app.repositories import notification_repository
from app.services import smtp_transport


def _maybe_email(session: Session, notification: AdminNotification) -> None:
    """Fires an optional email copy for a notification that was just
    created. Best-effort - a failed or skipped email never affects the
    notification itself, which is already saved in the database."""
    if not smtp_transport.is_configured():
        return

    if notification.recipient_admin_id:
        admin = session.get(AdminUser, notification.recipient_admin_id)
        recipient = admin.email if admin else None
    else:
        # Broadcast notification - goes to the configured ops inbox, if set.
        recipient = os.environ.get("LEAD_NOTIFICATION_EMAIL")

    if not recipient:
        return

    smtp_transport.send(to=recipient, subject=notification.title, body=notification.body or notification.title)


def notify_new_lead(session: Session, *, lead_id: str, service_key: str, city: Optional[str]) -> AdminNotification:
    """Broadcast to every admin/superadmin - no specific assignee yet."""
    notification = AdminNotification(
        recipient_admin_id=None,
        notification_type="new_lead",
        title=f"New {service_key.replace('_', ' ').title()} lead",
        body=f"A new lead came in{f' from {city}' if city else ''}.",
        related_type="lead",
        related_id=lead_id,
    )
    notification_repository.insert(session, notification)
    _maybe_email(session, notification)
    return notification


def notify_lead_assigned(
    session: Session, *, admin_id: str, lead_id: str, public_reference: str
) -> AdminNotification:
    notification = AdminNotification(
        recipient_admin_id=admin_id,
        notification_type="lead_assigned",
        title="A lead was assigned to you",
        body=f"Lead {public_reference} has been assigned to you.",
        related_type="lead",
        related_id=lead_id,
    )
    notification_repository.insert(session, notification)
    _maybe_email(session, notification)
    return notification


def notify_new_conversation(session: Session, *, conversation_id: str) -> AdminNotification:
    """Broadcast - fired the first time a brand-new conversation starts
    (see chat_service.py, which checks store.exists() before creating)."""
    notification = AdminNotification(
        recipient_admin_id=None,
        notification_type="new_conversation",
        title="New chat conversation started",
        body="A visitor started a new conversation with the chatbot.",
        related_type="conversation",
        related_id=conversation_id,
    )
    notification_repository.insert(session, notification)
    _maybe_email(session, notification)
    return notification


def notify_new_appointment(
    session: Session, *, appointment_id: str, appointment_type: str
) -> AdminNotification:
    """Broadcast - fired when a callback or consultation request is
    submitted (see appointment_service.request_appointment)."""
    label = "Consultation" if appointment_type == "consultation" else "Callback"
    notification = AdminNotification(
        recipient_admin_id=None,
        notification_type="appointment_booked",
        title=f"{label} requested",
        body=f"A customer requested a {appointment_type}.",
        related_type="appointment",
        related_id=appointment_id,
    )
    notification_repository.insert(session, notification)
    _maybe_email(session, notification)
    return notification


def notify_unanswered_question(
    session: Session, *, unknown_query_id: str, message: str
) -> AdminNotification:
    """Broadcast - fired when the chatbot logs a question it couldn't
    confidently answer (see knowledge_improvement_service.log_unknown_query)."""
    preview = message if len(message) <= 120 else message[:117] + "..."
    notification = AdminNotification(
        recipient_admin_id=None,
        notification_type="unanswered_question",
        title="Unanswered customer question",
        body=preview,
        related_type="unknown_query",
        related_id=unknown_query_id,
    )
    notification_repository.insert(session, notification)
    _maybe_email(session, notification)
    return notification


def list_unread(session: Session, *, admin_id: str) -> list[AdminNotification]:
    return notification_repository.list_for_admin(session, admin_id=admin_id, unread_only=True)


class NotificationNotFoundError(LookupError):
    pass


def mark_read(session: Session, *, notification_id: str) -> AdminNotification:
    notification = notification_repository.get(session, notification_id)
    if notification is None:
        raise NotificationNotFoundError(f"No notification with id '{notification_id}'.")
    notification.read = True
    return notification
