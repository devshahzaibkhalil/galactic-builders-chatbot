"""Admin authentication: Argon2id password hashing, login verification,
and brute-force lockout. This is the ONLY module that hashes or verifies
admin passwords — routes and models must never call argon2 directly.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.roles import SUPERADMIN
from app.models.admin_user import AdminUser
from app.security.password_policy import validate_password_strength
from app.services import mfa_service

_hasher = PasswordHasher()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


class WeakPasswordError(ValueError):
    pass


class AccountLockedError(RuntimeError):
    pass


class InvalidCredentialsError(RuntimeError):
    pass


def hash_password(raw_password: str) -> str:
    result = validate_password_strength(raw_password)
    if not result["valid"]:
        raise WeakPasswordError(result["message"] or "Password does not meet policy.")
    return _hasher.hash(raw_password)


def set_password(user: AdminUser, raw_password: str) -> None:
    """Used by the 'forgot password' reset flow. Also clears any existing
    lockout/failed-attempt state — a successful reset is a stronger proof
    of identity than a correct password guess, so there's no reason to
    leave the account locked out afterward."""
    user.password_hash = hash_password(raw_password)
    user.failed_login_count = 0
    user.locked_until = None


def verify_password(user: AdminUser, raw_password: str) -> bool:
    """Used by self-service account changes (email/username/password) to
    confirm the admin re-supplied their current password before the change
    is applied. Unlike authenticate(), this never touches lockout state -
    it's only ever called on an already-authenticated session."""
    try:
        _hasher.verify(user.password_hash, raw_password)
        return True
    except VerifyMismatchError:
        return False


def requires_mfa(user: AdminUser) -> bool:
    """Superadmins with MFA enabled must complete a second factor at login.
    Enforcement of "superadmins must have MFA enabled" as a hard policy
    (rather than opt-in) is a deployment/admin-onboarding decision, not
    this function's job — it only reports current state."""
    return user.role == SUPERADMIN and user.mfa_enabled


def begin_mfa_enrollment(user: AdminUser) -> tuple[str, str]:
    """Generates a new TOTP secret and provisioning URI. Caller must save
    the secret on the user (not yet marking mfa_enabled=True) until the
    admin confirms a valid code via confirm_mfa_enrollment()."""
    secret = mfa_service.generate_secret()
    uri = mfa_service.get_provisioning_uri(secret, user.email)
    return secret, uri


def confirm_mfa_enrollment(user: AdminUser, *, secret: str, code: str) -> bool:
    """Verifies the admin's authenticator app is actually working before
    committing to requiring MFA on every future login."""
    if not mfa_service.verify_code(secret, code):
        return False
    user.mfa_secret = secret
    user.mfa_enabled = True
    return True


def verify_mfa_login_code(user: AdminUser, code: str) -> bool:
    if not user.mfa_secret:
        return False
    return mfa_service.verify_code(user.mfa_secret, code)


def create_admin_user(
    session: Session, *, email: str, username: str, raw_password: str, role: str
) -> AdminUser:
    user = AdminUser(
        email=email.lower().strip(),
        username=username.strip(),
        password_hash=hash_password(raw_password),
        role=role,
    )
    session.add(user)
    session.flush()
    return user


def _is_locked(user: AdminUser) -> bool:
    if not user.locked_until:
        return False
    locked_until = user.locked_until
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return locked_until > datetime.now(timezone.utc)


def authenticate(session: Session, *, username_or_email: str, raw_password: str) -> AdminUser:
    """Verifies credentials, applying brute-force lockout.

    Raises AccountLockedError or InvalidCredentialsError rather than
    returning None, so callers can't accidentally treat a locked account
    the same as a wrong password in logging/messaging.
    """
    identifier = username_or_email.strip()
    user = session.execute(
        select(AdminUser).where(
            (AdminUser.email == identifier.lower()) | (AdminUser.username == identifier)
        )
    ).scalar_one_or_none()

    if user is None or not user.is_active:
        raise InvalidCredentialsError("Invalid username/email or password.")

    if _is_locked(user):
        raise AccountLockedError(
            f"Account is locked until {user.locked_until.isoformat()} due to repeated failed logins."
        )

    try:
        _hasher.verify(user.password_hash, raw_password)
    except VerifyMismatchError as exc:
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + LOCKOUT_DURATION
        raise InvalidCredentialsError("Invalid username/email or password.") from exc

    # Successful login.
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)

    if _hasher.check_needs_rehash(user.password_hash):
        user.password_hash = _hasher.hash(raw_password)

    return user
