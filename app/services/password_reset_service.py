"""Password reset tokens for the admin 'forgot password' flow.

Tokens are signed (itsdangerous), time-limited, and single-purpose (a
distinct salt keeps them from being replayed against any other token type
in the app, like the MFA pending token). Nothing is persisted server-side
for the token itself — expiry and validity are enforced purely by the
signature and the embedded timestamp, so there is no reset-token table to
clean up.
"""
from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

RESET_TOKEN_SALT = "admin-password-reset"
RESET_TOKEN_MAX_AGE_SECONDS = 30 * 60  # 30 minutes


def create_reset_token(*, user_id: str, secret_key: str) -> str:
    serializer = URLSafeTimedSerializer(secret_key, salt=RESET_TOKEN_SALT)
    return serializer.dumps({"user_id": user_id})


class ResetTokenExpiredError(RuntimeError):
    pass


class ResetTokenInvalidError(RuntimeError):
    pass


def verify_reset_token(token: str, *, secret_key: str) -> str:
    """Returns the user_id embedded in the token, or raises."""
    serializer = URLSafeTimedSerializer(secret_key, salt=RESET_TOKEN_SALT)
    try:
        data = serializer.loads(token, max_age=RESET_TOKEN_MAX_AGE_SECONDS)
    except SignatureExpired as exc:
        raise ResetTokenExpiredError("This reset link has expired.") from exc
    except BadSignature as exc:
        raise ResetTokenInvalidError("This reset link is invalid.") from exc
    return data["user_id"]
