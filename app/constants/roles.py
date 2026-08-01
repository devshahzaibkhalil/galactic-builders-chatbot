"""Admin role constants — single source of truth for role names.

app/security/permissions.py owns what each role is allowed to do; this
module only owns the role names themselves.
"""
from __future__ import annotations

AGENT = "agent"
ADMIN = "admin"
SUPERADMIN = "superadmin"

ALL_ROLES = (AGENT, ADMIN, SUPERADMIN)
