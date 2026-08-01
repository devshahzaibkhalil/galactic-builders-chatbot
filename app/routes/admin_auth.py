"""Admin login/logout. Session is rotated (cleared) before login_user() to
mitigate session fixation, per spec section 13.

Note: user_loader opens and closes a session per lookup, returning a
detached object (expire_on_commit=False makes already-loaded attributes
still readable). Any route that needs a fresh, attached AdminUser should
re-query via current_app.extensions["db_session_factory"]() rather than
relying on current_user for further DB operations.
"""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, session
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_wtf.csrf import generate_csrf
from sqlalchemy import select

from app.models.admin_user import AdminUser
from app.security.rate_limits import LOGIN_RATE_LIMIT, PASSWORD_RESET_RATE_LIMIT, limiter
from app.services.audit_service import record as record_audit
from app.services.authentication_service import (
    AccountLockedError,
    InvalidCredentialsError,
    WeakPasswordError,
    authenticate,
    requires_mfa,
    set_password,
    verify_mfa_login_code,
)
from app.services.mfa_pending_service import (
    MfaPendingExpiredError,
    MfaPendingInvalidError,
    create_pending_token,
    resolve_pending_token,
)
from app.services.password_reset_service import (
    ResetTokenExpiredError,
    ResetTokenInvalidError,
    create_reset_token,
    verify_reset_token,
)
from app.services.smtp_transport import send as send_email

admin_auth_bp = Blueprint("admin_auth", __name__, url_prefix="/admin")
login_manager = LoginManager()
login_manager.login_view = "admin_dashboard.login_page"


def init_login_manager(app):
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        db_session = current_app.extensions["db_session_factory"]()
        try:
            return db_session.get(AdminUser, user_id)
        finally:
            db_session.close()


@admin_auth_bp.get("/csrf-token")
def csrf_token():
    """Fetched by the admin dashboard before its first state-changing
    request (including login itself, since CSRFProtect covers this whole
    blueprint) — return the token as X-CSRFToken on subsequent POSTs."""
    return jsonify({"csrf_token": generate_csrf()})


@admin_auth_bp.post("/login")
@limiter.limit(LOGIN_RATE_LIMIT)
def login():
    payload = request.get_json(silent=True) or {}
    username_or_email = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not username_or_email or not password:
        return jsonify({"error": "username and password are required"}), 400

    db_session = current_app.extensions["db_session_factory"]()
    try:
        user = authenticate(db_session, username_or_email=username_or_email, raw_password=password)

        if requires_mfa(user):
            pending_token = create_pending_token(user_id=user.id, secret_key=current_app.config["SECRET_KEY"])
            record_audit(
                db_session,
                action="auth.mfa_challenge_issued",
                actor_id=user.id,
                actor_role=user.role,
                target_type="admin_user",
                target_id=user.id,
            )
            db_session.commit()
            return jsonify({"mfa_required": True, "mfa_pending_token": pending_token})

        record_audit(
            db_session,
            action="auth.login_success",
            actor_id=user.id,
            actor_role=user.role,
            target_type="admin_user",
            target_id=user.id,
        )
        db_session.commit()
    except AccountLockedError as exc:
        record_audit(db_session, action="auth.login_locked", metadata={"identifier": username_or_email})
        db_session.commit()  # persist the lockout timestamp even on failure
        return jsonify({"error": "account_locked", "message": str(exc)}), 423
    except InvalidCredentialsError:
        record_audit(db_session, action="auth.login_failed", metadata={"identifier": username_or_email})
        db_session.commit()  # persist the incremented failed_login_count
        return jsonify({"error": "invalid_credentials"}), 401
    finally:
        db_session.close()

    session.clear()  # session rotation — drop any pre-auth session data
    login_user(user)
    return jsonify({"id": user.id, "username": user.username, "role": user.role})


@admin_auth_bp.post("/login/mfa")
@limiter.limit(LOGIN_RATE_LIMIT)
def login_mfa():
    """Second step of superadmin login: exchanges the short-lived pending
    token plus a valid TOTP code for an actual session."""
    payload = request.get_json(silent=True) or {}
    pending_token = payload.get("mfa_pending_token")
    code = payload.get("code")

    if not pending_token or not code:
        return jsonify({"error": "mfa_pending_token and code are required"}), 400

    db_session = current_app.extensions["db_session_factory"]()
    try:
        try:
            user_id = resolve_pending_token(pending_token, secret_key=current_app.config["SECRET_KEY"])
        except MfaPendingExpiredError as exc:
            return jsonify({"error": "mfa_pending_expired", "message": str(exc)}), 410
        except MfaPendingInvalidError as exc:
            return jsonify({"error": "mfa_pending_invalid", "message": str(exc)}), 401

        user = db_session.get(AdminUser, user_id)
        if user is None or not user.is_active:
            return jsonify({"error": "mfa_pending_invalid"}), 401

        if not verify_mfa_login_code(user, code):
            record_audit(
                db_session, action="auth.mfa_code_invalid", actor_id=user.id, actor_role=user.role,
                target_type="admin_user", target_id=user.id,
            )
            db_session.commit()
            return jsonify({"error": "mfa_code_invalid"}), 401

        record_audit(
            db_session, action="auth.login_success", actor_id=user.id, actor_role=user.role,
            target_type="admin_user", target_id=user.id, metadata={"mfa": True},
        )
        db_session.commit()
    finally:
        db_session.close()

    session.clear()
    login_user(user)
    return jsonify({"id": user.id, "username": user.username, "role": user.role})


@admin_auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return jsonify({"status": "logged_out"})


@admin_auth_bp.get("/me")
@login_required
def me():
    return jsonify({"id": current_user.id, "username": current_user.username, "role": current_user.role})


@admin_auth_bp.post("/forgot-password")
@limiter.limit(PASSWORD_RESET_RATE_LIMIT)
def forgot_password():
    """Always returns the same generic response whether or not the email
    matches an account — revealing which emails have accounts would let an
    attacker enumerate your admin roster."""
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    generic_response = jsonify(
        {"message": "If that email matches an account, a reset link has been sent."}
    )

    if not email:
        return jsonify({"error": "email is required"}), 400

    db_session = current_app.extensions["db_session_factory"]()
    try:
        user = db_session.execute(
            select(AdminUser).where(AdminUser.email == email)
        ).scalar_one_or_none()

        if user is not None and user.is_active:
            token = create_reset_token(user_id=user.id, secret_key=current_app.config["SECRET_KEY"])
            reset_url = f"{request.url_root.rstrip('/')}/admin/dashboard/reset-password?token={token}"
            send_email(
                to=user.email,
                subject="Reset your Galactic Builders admin password",
                body=(
                    f"Hi {user.username},\n\n"
                    "A password reset was requested for your Galactic Builders admin account.\n"
                    f"Reset it here (valid for 30 minutes): {reset_url}\n\n"
                    "If you didn't request this, you can safely ignore this email."
                ),
            )
            record_audit(
                db_session,
                action="auth.password_reset_requested",
                actor_id=user.id,
                actor_role=user.role,
                target_type="admin_user",
                target_id=user.id,
            )
            db_session.commit()
    finally:
        db_session.close()

    return generic_response


@admin_auth_bp.post("/reset-password")
@limiter.limit(PASSWORD_RESET_RATE_LIMIT)
def reset_password():
    payload = request.get_json(silent=True) or {}
    token = payload.get("token") or ""
    new_password = payload.get("password") or ""

    if not token or not new_password:
        return jsonify({"error": "token and password are required"}), 400

    try:
        user_id = verify_reset_token(token, secret_key=current_app.config["SECRET_KEY"])
    except ResetTokenExpiredError:
        return jsonify({"error": "token_expired", "message": "This reset link has expired."}), 400
    except ResetTokenInvalidError:
        return jsonify({"error": "token_invalid", "message": "This reset link is invalid."}), 400

    db_session = current_app.extensions["db_session_factory"]()
    try:
        user = db_session.get(AdminUser, user_id)
        if user is None or not user.is_active:
            return jsonify({"error": "token_invalid", "message": "This reset link is invalid."}), 400

        try:
            set_password(user, new_password)
        except WeakPasswordError as exc:
            return jsonify({"error": "weak_password", "message": str(exc)}), 400

        record_audit(
            db_session,
            action="auth.password_reset_completed",
            actor_id=user.id,
            actor_role=user.role,
            target_type="admin_user",
            target_id=user.id,
        )
        db_session.commit()
    finally:
        db_session.close()

    return jsonify({"message": "Password updated. You can now sign in."})
