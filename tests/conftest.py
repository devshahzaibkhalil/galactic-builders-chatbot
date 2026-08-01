"""Session-wide pytest fixtures.

Sets FIELD_ENCRYPTION_KEY / BLIND_INDEX_KEY for the whole test session so
every test that touches Lead.email/Lead.phone (which are now transparently
encrypted at rest — see app/models/lead.py) works without each test file
setting this up itself. These are throwaway test-only keys, never used
outside pytest.
"""
from __future__ import annotations

import os

from cryptography.fernet import Fernet


def pytest_configure(config) -> None:
    os.environ.setdefault("FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    os.environ.setdefault("BLIND_INDEX_KEY", "test-only-blind-index-key-not-for-production")
