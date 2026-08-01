"""Conversation mode constants — single source of truth.

Do not redefine these strings anywhere else (routes, JS, templates); import
from here so a rename never has to touch more than one file.
"""
from __future__ import annotations

BOT_ACTIVE = "bot_active"
ADMIN_ACTIVE = "admin_active"
WAITING_FOR_CUSTOMER = "waiting_for_customer"
CLOSED = "closed"

ALL_MODES = (BOT_ACTIVE, ADMIN_ACTIVE, WAITING_FOR_CUSTOMER, CLOSED)
