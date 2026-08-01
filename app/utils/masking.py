"""Masks PII for display (e.g. an admin list view showing 'j***@example.com'
instead of the full address). Distinct from security/redaction.py, which
removes PII from logs entirely — masking keeps a recognizable, partial
value on purpose so an admin can still tell leads apart at a glance.
"""
from __future__ import annotations


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return email
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        masked_local = local[0] + "*" * max(len(local) - 1, 1)
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 4:
        return "*" * len(digits)
    last4 = digits[-4:]
    return f"(***) ***-{last4}"


def mask_street_address(address: str) -> str:
    """Keeps only the house number visible, e.g. '123 ***' — enough for an
    admin to sanity-check they have the right property without the full
    address sitting in a list view."""
    if not address:
        return address
    parts = address.strip().split(" ", 1)
    if len(parts) == 1:
        return "***"
    return f"{parts[0]} ***"
