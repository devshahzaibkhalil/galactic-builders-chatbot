"""Rate limiting via Flask-Limiter.

The admin login endpoint gets its own, tighter limit on top of the
per-account lockout in authentication_service.py — the lockout stops one
account from being brute-forced, this stops one IP from hammering the
endpoint across many different usernames.
"""
from __future__ import annotations

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["200 per minute"])

LOGIN_RATE_LIMIT = "10 per minute"
CHAT_MESSAGE_RATE_LIMIT = "60 per minute"
LEAD_SUBMISSION_RATE_LIMIT = "10 per hour"
UPLOAD_RATE_LIMIT = "30 per hour"
APPOINTMENT_RATE_LIMIT = "10 per hour"
BOOKMARK_RATE_LIMIT = "20 per hour"


def init_rate_limits(app: Flask) -> None:
    limiter.init_app(app)
