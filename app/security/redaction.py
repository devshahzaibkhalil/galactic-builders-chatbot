"""Redacts PII from strings before they reach a log sink.

Intended to be applied inside a logging Filter/Formatter (see
logging_config.py, a later phase) so nothing upstream needs to remember to
redact — every log record passes through this on the way out. Pattern-based
and intentionally conservative: it's fine to over-redact in logs, it is not
fine to under-redact.
"""
from __future__ import annotations

import re

_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE_PATTERN = re.compile(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]?){13,19}\b")

_REDACTED = "[REDACTED]"

_DEFAULT_SENSITIVE_KEYS = frozenset({
    "email", "phone", "password", "raw_password", "ssn", "credit_card",
    "street_address", "mfa_secret", "password_hash",
})


def redact(text: str) -> str:
    if not text:
        return text
    text = _EMAIL_PATTERN.sub(_REDACTED, text)
    text = _PHONE_PATTERN.sub(_REDACTED, text)
    text = _SSN_PATTERN.sub(_REDACTED, text)
    text = _CREDIT_CARD_PATTERN.sub(_REDACTED, text)
    return text


def redact_dict(data: dict, *, sensitive_keys: frozenset = _DEFAULT_SENSITIVE_KEYS) -> dict:
    """Redacts by key name (for structured log payloads) in addition to
    pattern-based redaction on string values."""
    result = {}
    for key, value in data.items():
        if key.lower() in sensitive_keys:
            result[key] = _REDACTED
        elif isinstance(value, str):
            result[key] = redact(value)
        elif isinstance(value, dict):
            result[key] = redact_dict(value, sensitive_keys=sensitive_keys)
        else:
            result[key] = value
    return result
