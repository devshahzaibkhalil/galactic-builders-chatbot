from __future__ import annotations

from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.models.admin_user import AdminUser
from app.security.permissions import PermissionDeniedError, require_permission
from app.services import dashboard_settings_service, smtp_transport
from app.services.audit_service import record as record_audit
from app.services.authentication_service import WeakPasswordError, set_password, verify_password
from app.services.dashboard_settings_service import InvalidColorError, get_theme, reset_theme, update_theme
from app.validators.email_validator import validate_email
from app.validators.username_validator import validate_username

admin_settings_bp = Blueprint("admin_settings", __name__, url_prefix="/admin/settings")


def _require(action: str):
    def decorator(view_fn):
        @wraps(view_fn)
        def wrapped(*args, **kwargs):
            try:
                require_permission(current_user.role, action)
            except PermissionDeniedError:
                return jsonify({"error": "permission_denied"}), 403
            return view_fn(*args, **kwargs)
        return wrapped
    return decorator


@admin_settings_bp.get("")
@login_required
def get_settings():
    session_factory = current_app.extensions["db_session_factory"]
    session = session_factory()
    try:
        theme = get_theme(session)
        session.commit()
        result = {"primary_color": theme.primary_color, "accent_color": theme.accent_color}
    finally:
        session.close()
    return jsonify(result)


@admin_settings_bp.put("")
@login_required
@_require("manage_appearance")
def update_settings():
    payload = request.get_json(silent=True) or {}
    primary_color = payload.get("primary_color")
    accent_color = payload.get("accent_color")

    if not primary_color or not accent_color:
        return jsonify({"error": "primary_color and accent_color are required"}), 400

    session_factory = current_app.extensions["db_session_factory"]
    session = session_factory()
    try:
        try:
            theme = update_theme(session, primary_color=primary_color, accent_color=accent_color)
        except InvalidColorError as exc:
            return jsonify({"error": "invalid_color", "message": str(exc)}), 422

        record_audit(
            session,
            action="settings.appearance_update",
            actor_id=current_user.id,
            actor_role=current_user.role,
            target_type="dashboard_setting",
            target_id=theme.id,
            metadata={"primary_color": primary_color, "accent_color": accent_color},
        )
        session.commit()
        result = {"primary_color": theme.primary_color, "accent_color": theme.accent_color}
    finally:
        session.close()

    return jsonify(result)


@admin_settings_bp.post("/reset")
@login_required
@_require("manage_appearance")
def reset_settings():
    session_factory = current_app.extensions["db_session_factory"]
    session = session_factory()
    try:
        theme = reset_theme(session)
        record_audit(
            session, action="settings.appearance_reset", actor_id=current_user.id, actor_role=current_user.role,
            target_type="dashboard_setting", target_id=theme.id,
        )
        session.commit()
        result = {"primary_color": theme.primary_color, "accent_color": theme.accent_color}
    finally:
        session.close()
    return jsonify(result)


# ---------------------------------------------------------------------------
# My account: every admin/agent can view and change their own email,
# username, and password (never anyone else's - there's no "target user id"
# here, only current_user).
# ---------------------------------------------------------------------------

@admin_settings_bp.get("/account")
@login_required
def get_account():
    return jsonify({"email": current_user.email, "username": current_user.username, "role": current_user.role})


@admin_settings_bp.put("/account")
@login_required
def update_account():
    payload = request.get_json(silent=True) or {}
    new_email = (payload.get("email") or "").strip()
    new_username = (payload.get("username") or "").strip()
    current_password = payload.get("current_password") or ""

    if not new_email or not new_username:
        return jsonify({"error": "email and username are required"}), 400
    if not current_password:
        return jsonify({"error": "current_password is required"}), 400

    email_result = validate_email(new_email)
    if not email_result["valid"]:
        return jsonify({"error": email_result["error_code"], "message": email_result["message"]}), 422

    username_result = validate_username(new_username)
    if not username_result["valid"]:
        return jsonify({"error": username_result["error_code"], "message": username_result["message"]}), 422

    session_factory = current_app.extensions["db_session_factory"]
    session = session_factory()
    try:
        user = session.get(AdminUser, current_user.id)
        if user is None or not verify_password(user, current_password):
            return jsonify({"error": "invalid_current_password", "message": "Current password is incorrect."}), 401

        user.email = email_result["normalized_value"]
        user.username = username_result["normalized_value"]

        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            return jsonify({"error": "already_in_use", "message": "That email or username is already taken."}), 409

        record_audit(
            session,
            action="settings.account_update",
            actor_id=user.id,
            actor_role=user.role,
            target_type="admin_user",
            target_id=user.id,
            metadata={"email": user.email, "username": user.username},
        )
        session.commit()
        result = {"email": user.email, "username": user.username, "role": user.role}
    finally:
        session.close()

    return jsonify(result)


@admin_settings_bp.put("/password")
@login_required
def update_password():
    payload = request.get_json(silent=True) or {}
    current_password = payload.get("current_password") or ""
    new_password = payload.get("new_password") or ""

    if not current_password or not new_password:
        return jsonify({"error": "current_password and new_password are required"}), 400

    session_factory = current_app.extensions["db_session_factory"]
    session = session_factory()
    try:
        user = session.get(AdminUser, current_user.id)
        if user is None or not verify_password(user, current_password):
            return jsonify({"error": "invalid_current_password", "message": "Current password is incorrect."}), 401

        try:
            set_password(user, new_password)
        except WeakPasswordError as exc:
            return jsonify({"error": "weak_password", "message": str(exc)}), 400

        record_audit(
            session,
            action="settings.password_change",
            actor_id=user.id,
            actor_role=user.role,
            target_type="admin_user",
            target_id=user.id,
        )
        session.commit()
    finally:
        session.close()

    return jsonify({"message": "Password updated."})


# ---------------------------------------------------------------------------
# Lead notification email: where broadcast admin notifications (new lead,
# new conversation, appointment requested, unanswered question) get emailed.
# Superadmin-only - same permission that already existed for this purpose.
# ---------------------------------------------------------------------------

@admin_settings_bp.get("/notifications")
@login_required
@_require("configure_notification_recipients")
def get_notification_settings():
    session_factory = current_app.extensions["db_session_factory"]
    session = session_factory()
    try:
        info = dashboard_settings_service.get_lead_notification_email_source(session)
        session.commit()
    finally:
        session.close()
    return jsonify({"lead_notification_email": info["email"], "source": info["source"]})


@admin_settings_bp.put("/notifications")
@login_required
@_require("configure_notification_recipients")
def update_notification_settings():
    payload = request.get_json(silent=True) or {}
    # Empty string / omitted clears the override and falls back to the
    # LEAD_NOTIFICATION_EMAIL env var again.
    raw_email = payload.get("lead_notification_email")

    session_factory = current_app.extensions["db_session_factory"]
    session = session_factory()
    try:
        try:
            setting = dashboard_settings_service.update_lead_notification_email(session, raw_email)
        except dashboard_settings_service.InvalidNotificationEmailError as exc:
            return jsonify({"error": "invalid_email", "message": str(exc)}), 422

        record_audit(
            session,
            action="settings.lead_notification_email_update",
            actor_id=current_user.id,
            actor_role=current_user.role,
            target_type="dashboard_setting",
            target_id=setting.id,
            metadata={"lead_notification_email": setting.lead_notification_email},
        )
        session.commit()
        info = dashboard_settings_service.get_lead_notification_email_source(session)
        session.commit()
    finally:
        session.close()

    return jsonify({"lead_notification_email": info["email"], "source": info["source"]})


# ---------------------------------------------------------------------------
# Email diagnostics
# ---------------------------------------------------------------------------

@admin_settings_bp.get("/email-diagnostics")
@login_required
@_require("configure_notification_recipients")
def email_diagnostics():
    """Reports whether outbound email can actually work, without sending.

    Every value is reported as set/not-set only; no key or secret is ever
    returned in the response body.
    """
    session_factory = current_app.extensions["db_session_factory"]
    session = session_factory()
    try:
        info = dashboard_settings_service.get_lead_notification_email_source(session)
        session.commit()
    finally:
        session.close()

    provider = smtp_transport.active_provider()
    from_address = smtp_transport._from_address()

    checks = {
        "provider": provider,
        "configured": smtp_transport.is_configured(),
        "from_address": from_address or None,
        "from_name": smtp_transport._from_name(),
        "recipient": info["email"],
        "recipient_source": info["source"],
    }
    if provider == "mailjet":
        checks["mailjet_api_key_set"] = bool(smtp_transport._clean("MAILJET_API_KEY"))
        checks["mailjet_secret_key_set"] = bool(smtp_transport._clean("MAILJET_SECRET_KEY"))
    else:
        checks["smtp_host_set"] = bool(smtp_transport._clean("SMTP_HOST"))

    problems = []
    if not checks["configured"]:
        if provider == "mailjet":
            problems.append(
                "Mailjet is not fully configured. Both MAILJET_API_KEY and "
                "MAILJET_SECRET_KEY must be set."
            )
        else:
            problems.append("SMTP_HOST is not set.")
    if not from_address:
        problems.append("EMAIL_FROM_ADDRESS is not set, so there is no sender address.")
    if not checks["recipient"]:
        problems.append(
            "No lead notification recipient. Set one in Settings -> Lead notifications "
            "or via the LEAD_NOTIFICATION_EMAIL environment variable."
        )

    checks["problems"] = problems
    checks["ready"] = not problems
    return jsonify(checks)


@admin_settings_bp.post("/email-diagnostics/test")
@login_required
@_require("configure_notification_recipients")
def email_diagnostics_test():
    """Sends a real test email and reports the outcome.

    On failure the reason is written to the application log by
    smtp_transport; check the Render Logs tab for the provider's exact
    response.
    """
    payload = request.get_json(silent=True) or {}
    recipient = (payload.get("recipient") or "").strip()

    session_factory = current_app.extensions["db_session_factory"]
    session = session_factory()
    try:
        if not recipient:
            recipient = dashboard_settings_service.get_lead_notification_email(session) or ""
        session.commit()
    finally:
        session.close()

    if not recipient:
        return jsonify({
            "sent": False,
            "error": "no_recipient",
            "message": "No recipient configured and none supplied.",
        }), 422

    result = validate_email(recipient)
    if not result["valid"]:
        return jsonify({
            "sent": False,
            "error": "invalid_email",
            "message": result["message"] or "Invalid email address.",
        }), 422

    sent = smtp_transport.send(
        to=result["normalized_value"],
        subject="Galactic Builders email test",
        body=(
            "Outbound email is configured correctly. New lead notifications "
            "will be delivered automatically."
        ),
    )
    return jsonify({
        "sent": sent,
        "provider": smtp_transport.active_provider(),
        "recipient": result["normalized_value"],
        "message": (
            "Test email sent."
            if sent else
            "Send failed. Check the application logs for the provider's exact response."
        ),
    }), (200 if sent else 502)
