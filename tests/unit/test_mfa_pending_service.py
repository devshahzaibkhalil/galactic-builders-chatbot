import time

import pytest

from app.services.mfa_pending_service import (
    MfaPendingExpiredError,
    MfaPendingInvalidError,
    create_pending_token,
    resolve_pending_token,
)

SECRET = "test-secret"


def test_valid_token_resolves_to_user_id():
    token = create_pending_token(user_id="user-123", secret_key=SECRET)
    assert resolve_pending_token(token, secret_key=SECRET) == "user-123"


def test_expired_token_rejected():
    token = create_pending_token(user_id="user-123", secret_key=SECRET)
    time.sleep(2.1)
    with pytest.raises(MfaPendingExpiredError):
        resolve_pending_token(token, secret_key=SECRET, max_age_seconds=1)


def test_tampered_token_rejected():
    token = create_pending_token(user_id="user-123", secret_key=SECRET)
    tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")
    with pytest.raises(MfaPendingInvalidError):
        resolve_pending_token(tampered, secret_key=SECRET)


def test_wrong_secret_rejected():
    token = create_pending_token(user_id="user-123", secret_key=SECRET)
    with pytest.raises(MfaPendingInvalidError):
        resolve_pending_token(token, secret_key="different-secret")
