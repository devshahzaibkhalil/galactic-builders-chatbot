from __future__ import annotations

from flask import Blueprint, current_app, jsonify
from flask_login import current_user, login_required

from app.services.notification_service import NotificationNotFoundError, list_unread, mark_read

admin_notifications_bp = Blueprint("admin_notifications", __name__, url_prefix="/admin/notifications")


@admin_notifications_bp.get("")
@login_required
def get_notifications():
    session_factory = current_app.extensions["db_session_factory"]
    session = session_factory()
    try:
        notifications = list_unread(session, admin_id=current_user.id)
        results = [
            {
                "id": n.id,
                "notification_type": n.notification_type,
                "title": n.title,
                "body": n.body,
                "related_type": n.related_type,
                "related_id": n.related_id,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ]
    finally:
        session.close()

    return jsonify({"notifications": results})


@admin_notifications_bp.post("/<notification_id>/read")
@login_required
def read_notification(notification_id: str):
    session_factory = current_app.extensions["db_session_factory"]
    session = session_factory()
    try:
        try:
            mark_read(session, notification_id=notification_id)
        except NotificationNotFoundError:
            return jsonify({"error": "notification_not_found"}), 404
        session.commit()
    finally:
        session.close()

    return jsonify({"status": "read"})
