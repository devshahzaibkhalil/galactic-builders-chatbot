"""Sends email over real SMTP. Entirely optional: if SMTP_HOST is not set
in the environment, is_configured() returns False and send() is a no-op
that logs and returns — nothing in the app requires this to function.

No credentials are stored anywhere except the environment variables the
admin explicitly sets (SMTP_HOST/PORT/USERNAME/PASSWORD). Failures here are
swallowed and logged rather than raised, since a notification email should
never be able to break the request that triggered it (lead submission,
appointment booking, etc.).
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger("galactic.smtp_transport")


def is_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST"))


def send(*, to: str, subject: str, body: str) -> bool:
    """Best-effort send. Returns True on success, False on any failure or
    if SMTP isn't configured — callers should treat this as "fire and
    forget", never let it block or fail the surrounding request."""
    if not is_configured():
        logger.info("SMTP not configured — skipping email to %s (%s)", to, subject)
        return False

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT") or 587)
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    use_tls = (os.environ.get("SMTP_USE_TLS", "true").lower() != "false")
    from_name = os.environ.get("EMAIL_FROM_NAME", "Galactic Builders")
    from_address = os.environ.get("EMAIL_FROM_ADDRESS") or username

    if not from_address:
        logger.warning("SMTP configured but EMAIL_FROM_ADDRESS/SMTP_USERNAME missing — skipping send")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{from_name} <{from_address}>"
    message["To"] = to
    message.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(message)
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False
