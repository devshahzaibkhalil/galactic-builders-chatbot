"""Bridges the two steps of superadmin login: password verification and TOTP
verification. The pending token is short-lived (5 minutes) and signed, so a
partially-authenticated session can't be replayed or extended — if the
second factor isn't provided quickly, the customer must start over from
the password step.
"""
from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

_SALT = "mfa-pending-v1"
DEFAULT_MAX_AGE_SECONDS = 5 * 60


class MfaPendingExpiredError(RuntimeError):
    pass


class MfaPendingInvalidError(RuntimeError):
    pass


def create_pending_token(*, user_id: str, secret_key: str) -> str:
    return URLSafeTimedSerializer(secret_key, salt=_SALT).dumps({"uid": user_id})


def resolve_pending_token(token: str, *, secret_key: str, max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS) -> str:
    try:
        payload = URLSafeTimedSerializer(secret_key, salt=_SALT).loads(token, max_age=max_age_seconds)
    except SignatureExpired as exc:
        raise MfaPendingExpiredError("This login attempt has expired. Please sign in again.") from exc
    except BadSignature as exc:
        raise MfaPendingInvalidError("This login attempt is not valid.") from exc

    user_id = payload.get("uid")
    if not user_id:
        raise MfaPendingInvalidError("This login attempt is not valid.")
    return user_id
