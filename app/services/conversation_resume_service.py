"""Conversation Bookmark (spec 16.4): lets a returning customer resume an
incomplete estimate request securely.

- The token is signed and time-limited (itsdangerous), never a raw/guessable
  database id — a UUID conversation_id is already fine to embed since it is
  unguessable and non-sequential, but we still never resolve a bookmark to
  saved data without a second factor.
- Resuming requires the customer to re-supply the email or phone they gave
  earlier ("identity confirmation before showing sensitive saved data").
  We store only a salted hash of that value in the token, never the value
  itself, and compare with a constant-time check.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

DEFAULT_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # 7 days
_TOKEN_SALT = "conversation-bookmark-v1"


class BookmarkExpiredError(RuntimeError):
    pass


class BookmarkInvalidError(RuntimeError):
    pass


class IdentityMismatchError(RuntimeError):
    pass


@dataclass
class BookmarkPayload:
    conversation_id: str
    contact_hash: str


def _hash_contact(contact_value: str, pepper: str) -> str:
    normalized = contact_value.strip().lower()
    return hashlib.sha256(f"{pepper}:{normalized}".encode("utf-8")).hexdigest()


def _serializer(secret_key: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key, salt=_TOKEN_SALT)


def create_bookmark_token(*, conversation_id: str, contact_value: str, secret_key: str) -> str:
    """contact_value is the email or phone the customer already gave earlier
    in the flow — never a new piece of data collected just for this."""
    pepper = secret_key  # reuse app secret as the hashing pepper; never logged
    payload = {"cid": conversation_id, "ch": _hash_contact(contact_value, pepper)}
    return _serializer(secret_key).dumps(payload)


def resolve_bookmark_token(
    token: str, *, provided_contact_value: str, secret_key: str, max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS
) -> str:
    """Returns the conversation_id if the token is valid, unexpired, and the
    provided contact value matches what was used to create it. Raises a
    specific error otherwise — callers must not treat any of these the same
    as "found nothing", since that would leak which failure occurred to a
    guessing attacker in a differently-worded response if they're not
    careful. (Route layer should still return a generic message either way.)
    """
    try:
        payload = _serializer(secret_key).loads(token, max_age=max_age_seconds)
    except SignatureExpired as exc:
        raise BookmarkExpiredError("This saved link has expired.") from exc
    except BadSignature as exc:
        raise BookmarkInvalidError("This saved link is not valid.") from exc

    expected_hash = payload.get("ch")
    conversation_id = payload.get("cid")
    if not expected_hash or not conversation_id:
        raise BookmarkInvalidError("This saved link is not valid.")

    actual_hash = _hash_contact(provided_contact_value, secret_key)
    if not hmac.compare_digest(expected_hash, actual_hash):
        raise IdentityMismatchError(
            "We couldn't verify your identity. Please provide the email or phone number used earlier."
        )

    return conversation_id
