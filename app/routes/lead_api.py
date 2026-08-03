from __future__ import annotations

import logging
import os

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.orm import Session

from app.jobs.email_jobs import attempt_notification
from app.models.email_notification import EmailNotification
from app.models.lead import Lead
from app.security.rate_limits import LEAD_SUBMISSION_RATE_LIMIT, limiter
from app.services import dashboard_settings_service, smtp_transport
from app.services.email_service import send_admin_notification, send_customer_confirmation
from app.services.lead_service import (
    InterestNotConfirmedError,
    LeadValidationError,
    submit_lead,
)

lead_api_bp = Blueprint("lead_api", __name__, url_prefix="/api/leads")
logger = logging.getLogger("galactic.lead_api")


def _transport(*, to: str, subject: str, body: str) -> None:
    """Adapts smtp_transport's best-effort bool return into the raise-on-
    failure contract app/jobs/email_jobs.attempt_notification expects, so a
    failed send gets recorded as RETRYING/FAILED on the notification row
    instead of silently disappearing."""
    if not smtp_transport.send(to=to, subject=subject, body=body):
        raise RuntimeError(f"SMTP send failed or is not configured (to={to!r}).")


def _send_lead_email(session: Session, lead_id: str, notification_type: str) -> None:
    """Sends the queued lead email immediately, in-request. This is a
    synchronous stand-in for the real Redis/RQ worker described in
    app/jobs/email_jobs.py — same retry-tracking logic (attempt_notification),
    just triggered right here instead of by a scheduler. Never raises: a
    slow/broken SMTP server can't fail the lead submission that already
    committed (submit_lead only calls this after session.commit()).
    """
    lead = session.get(Lead, lead_id)
    if lead is None:
        return

    notification = (
        session.query(EmailNotification)
        .filter_by(lead_id=lead_id, notification_type=notification_type)
        .order_by(EmailNotification.created_at.desc())
        .first()
    )
    if notification is None:
        return

    def _send(_notification: EmailNotification) -> None:
        if notification_type == "admin_lead":
            # Resolve through dashboard_settings_service so a recipient saved
            # in Admin -> Settings -> Lead notifications is honoured. It falls
            # back to the LEAD_NOTIFICATION_EMAIL env var on its own. Reading
            # the env var directly here used to bypass the dashboard override
            # entirely, so a dashboard-only configuration silently sent nothing.
            recipient = dashboard_settings_service.get_lead_notification_email(session)
            if not recipient:
                raise RuntimeError(
                    "No lead notification recipient configured. Set one in Admin -> "
                    "Settings -> Lead notifications, or set the LEAD_NOTIFICATION_EMAIL "
                    "environment variable."
                )
            dashboard_url = os.environ.get("ADMIN_DASHBOARD_URL", "")
            send_admin_notification(lead, recipient=recipient, dashboard_url=dashboard_url, transport=_transport)
        elif notification_type == "customer_confirmation":
            send_customer_confirmation(lead, transport=_transport)

    attempt_notification(session, notification, _send)
    session.commit()


@lead_api_bp.post("")
@limiter.limit(LEAD_SUBMISSION_RATE_LIMIT)
def create_lead():
    payload = request.get_json(silent=True) or {}
    session_factory = current_app.extensions["db_session_factory"]
    session = session_factory()

    try:
        lead = submit_lead(
            session,
            payload,
            queue_email=lambda lead_id, notification_type: _send_lead_email(session, lead_id, notification_type),
        )
    except LeadValidationError as exc:
        return jsonify({"error": "validation_failed", "fields": exc.errors}), 422
    except InterestNotConfirmedError as exc:
        return jsonify({"error": "interest_not_confirmed", "message": str(exc)}), 409
    finally:
        session.close()

    return jsonify({
        "public_reference": lead.public_reference,
        "status": lead.status.value,
    }), 201
