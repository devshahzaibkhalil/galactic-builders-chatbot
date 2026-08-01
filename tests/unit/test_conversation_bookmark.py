import time

import pytest

from app.services.conversation_resume_service import (
    BookmarkExpiredError,
    BookmarkInvalidError,
    IdentityMismatchError,
    create_bookmark_token,
    resolve_bookmark_token,
)

SECRET = "test-secret-key"


def test_valid_token_resolves_to_conversation_id():
    token = create_bookmark_token(conversation_id="conv-123", contact_value="jordan@example.com", secret_key=SECRET)
    resolved = resolve_bookmark_token(token, provided_contact_value="jordan@example.com", secret_key=SECRET)
    assert resolved == "conv-123"


def test_identity_mismatch_rejected():
    token = create_bookmark_token(conversation_id="conv-123", contact_value="jordan@example.com", secret_key=SECRET)
    with pytest.raises(IdentityMismatchError):
        resolve_bookmark_token(token, provided_contact_value="someone-else@example.com", secret_key=SECRET)


def test_contact_matching_is_case_and_whitespace_insensitive():
    token = create_bookmark_token(conversation_id="conv-123", contact_value="Jordan@Example.com", secret_key=SECRET)
    resolved = resolve_bookmark_token(token, provided_contact_value="  jordan@example.com  ", secret_key=SECRET)
    assert resolved == "conv-123"


def test_expired_token_rejected():
    token = create_bookmark_token(conversation_id="conv-123", contact_value="jordan@example.com", secret_key=SECRET)
    time.sleep(2.1)
    with pytest.raises(BookmarkExpiredError):
        resolve_bookmark_token(
            token, provided_contact_value="jordan@example.com", secret_key=SECRET, max_age_seconds=1
        )


def test_tampered_token_rejected():
    token = create_bookmark_token(conversation_id="conv-123", contact_value="jordan@example.com", secret_key=SECRET)
    tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")
    with pytest.raises(BookmarkInvalidError):
        resolve_bookmark_token(tampered, provided_contact_value="jordan@example.com", secret_key=SECRET)


def test_token_does_not_contain_plaintext_contact_value():
    token = create_bookmark_token(conversation_id="conv-123", contact_value="jordan@example.com", secret_key=SECRET)
    assert "jordan" not in token.lower()
    assert "example.com" not in token.lower()


def test_wrong_secret_key_rejected():
    token = create_bookmark_token(conversation_id="conv-123", contact_value="jordan@example.com", secret_key=SECRET)
    with pytest.raises(BookmarkInvalidError):
        resolve_bookmark_token(token, provided_contact_value="jordan@example.com", secret_key="a-different-secret")
