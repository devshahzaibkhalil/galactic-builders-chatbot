from __future__ import annotations

from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from app.security.permissions import PermissionDeniedError, require_permission
from app.services.audit_service import record as record_audit
from app.services.dashboard_settings_service import InvalidColorError, get_theme, reset_theme, update_theme

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
