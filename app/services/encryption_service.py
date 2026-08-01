"""Higher-level field encryption: wraps app/security/encryption.py and adds
a blind index (deterministic HMAC) so an encrypted field like email can
still be looked up with an equality query without ever storing or querying
the plaintext.

Usage pattern once wired onto a model: store `encrypt_field(value)` in the
real column and `compute_blind_index(value)` in a paired indexed column;
look up rows with `WHERE email_blind_index = compute_blind_index(query)`,
never `WHERE email = ...` against the encrypted value.

Not yet wired onto the Lead model — this phase delivers the encryption
primitive itself, fully tested; applying it to specific columns is a
follow-up migration since it touches lead_service, lead_repository, and
every place a lead's email/phone is currently read in plaintext.
"""
from __future__ import annotations

import hashlib
import hmac

from app.security.encryption import decrypt, encrypt


def encrypt_field(value: str, *, key: str) -> str:
    return encrypt(value, key=key)


def decrypt_field(ciphertext: str, *, key: str) -> str:
    return decrypt(ciphertext, key=key)


def compute_blind_index(value: str, *, blind_index_key: str) -> str:
    """Deterministic (same input -> same output) so it's safe as a lookup
    column, but not decryptable back to the original value. Normalizes
    case/whitespace first so 'Jordan@Example.com' and 'jordan@example.com'
    produce the same index, matching how email lookups are normally done."""
    normalized = value.strip().lower()
    return hmac.new(
        blind_index_key.encode("utf-8"), normalized.encode("utf-8"), hashlib.sha256
    ).hexdigest()
