"""Symmetric field-level encryption for sensitive stored data.

Uses Fernet (AES-128-CBC + HMAC-SHA256, authenticated encryption) keyed by
FIELD_ENCRYPTION_KEY from the environment. This module only encrypts/
decrypts opaque strings — deciding *which* fields get encrypted is
encryption_service.py's job, and this module never sees a database model.
"""
from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken


class EncryptionKeyMissingError(RuntimeError):
    pass


class DecryptionError(RuntimeError):
    pass


def generate_key() -> str:
    """Used by scripts/rotate_encryption_key.py and initial setup — never
    called in the request/response path."""
    return Fernet.generate_key().decode("ascii")


def get_field_encryption_key() -> str:
    """Resolves FIELD_ENCRYPTION_KEY from the environment.

    Read lazily (not cached at import time) so tests can set/override the
    env var per-session via a fixture without import-order issues — see
    tests/conftest.py.
    """
    key = os.environ.get("FIELD_ENCRYPTION_KEY", "")
    if not key:
        raise EncryptionKeyMissingError(
            "FIELD_ENCRYPTION_KEY is not set. Required to read/write encrypted lead fields."
        )
    return key


def get_blind_index_key() -> str:
    key = os.environ.get("BLIND_INDEX_KEY", "")
    if not key:
        raise EncryptionKeyMissingError(
            "BLIND_INDEX_KEY is not set. Required to read/write encrypted lead fields."
        )
    return key


def encrypt(plaintext: str, *, key: str) -> str:
    if not key:
        raise EncryptionKeyMissingError("FIELD_ENCRYPTION_KEY is not configured.")
    fernet = Fernet(key.encode("ascii"))
    return fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(ciphertext: str, *, key: str) -> str:
    if not key:
        raise EncryptionKeyMissingError("FIELD_ENCRYPTION_KEY is not configured.")
    fernet = Fernet(key.encode("ascii"))
    try:
        return fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise DecryptionError("Ciphertext could not be decrypted with the provided key.") from exc
