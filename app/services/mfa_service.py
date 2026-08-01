"""Multi-factor authentication (TOTP) for superadmin accounts.

Only this module touches pyotp — nothing else generates or verifies a code
directly. Superadmin MFA enforcement (requiring this at login) lives in
authentication_service.py / admin_auth.py; this module is pure TOTP
mechanics.
"""
from __future__ import annotations

import pyotp

ISSUER_NAME = "Galactic Builders Admin"


def generate_secret() -> str:
    return pyotp.random_base32()


def get_provisioning_uri(secret: str, account_email: str) -> str:
    """otpauth:// URI to render as a QR code during MFA setup."""
    return pyotp.totp.TOTP(secret).provisioning_uri(name=account_email, issuer_name=ISSUER_NAME)


def verify_code(secret: str, code: str, *, valid_window: int = 1) -> bool:
    """valid_window=1 tolerates minor clock drift (accepts the previous and
    next 30-second window in addition to the current one)."""
    if not code or not code.strip().isdigit():
        return False
    totp = pyotp.totp.TOTP(secret)
    return totp.verify(code.strip(), valid_window=valid_window)


def current_code(secret: str) -> str:
    """Test/admin-setup helper — generates the code that would currently
    validate. Never exposed to a customer-facing endpoint."""
    return pyotp.totp.TOTP(secret).now()
