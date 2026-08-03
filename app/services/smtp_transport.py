"""Sends outbound email.

Despite the module name (kept so every existing import keeps working), the
default transport is the Mailjet HTTPS API, not raw SMTP. Render blocks
outbound SMTP ports 25/465/587 on free instances and blocks port 25 on every
instance, so an smtplib connection there fails or hangs until it times out.
An HTTPS POST is never blocked.

Two transports are supported:

  mailjet  (default)  Set MAILJET_API_KEY and MAILJET_SECRET_KEY. Mailjet
                      verifies a single sender address by emailing it a
                      confirmation link, so no domain DNS access is needed.
  smtp                Set SMTP_HOST etc. Retained for local development and
                      for self-hosting outside Render.

EMAIL_PROVIDER forces one explicitly ("mailjet" or "smtp"); otherwise the
transport is inferred from whichever credentials are present.

No credentials are stored anywhere except the environment variables the admin
explicitly sets. Failures are swallowed and logged rather than raised, since a
notification email should never be able to break the request that triggered it
(lead submission, appointment booking, etc.).
"""
from __future__ import annotations

import base64
import json
import logging
import os
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage
from email.utils import formataddr

logger = logging.getLogger("galactic.smtp_transport")

MAILJET_API_URL = "https://api.mailjet.com/v3.1/send"
MAIL_TIMEOUT = 20


def _clean(name: str) -> str:
    """Read an env var, stripping whitespace and stray wrapping quotes.

    Render stores environment values literally, so a value pasted from a .env
    file as EMAIL_FROM_NAME="Galactic Builders" keeps its quote characters.
    Those quotes end up inside the From header and providers reject it.
    """
    value = os.environ.get(name) or ""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1].strip()
    return value


def active_provider() -> str:
    """Which transport to use: 'mailjet' or 'smtp'."""
    forced = _clean("EMAIL_PROVIDER").lower()
    if forced in {"mailjet", "smtp"}:
        return forced
    if _clean("MAILJET_API_KEY"):
        return "mailjet"
    if _clean("SMTP_HOST"):
        return "smtp"
    return "mailjet"


def is_configured() -> bool:
    """True when the active transport has everything it needs to send."""
    if active_provider() == "mailjet":
        return bool(_clean("MAILJET_API_KEY") and _clean("MAILJET_SECRET_KEY"))
    return bool(_clean("SMTP_HOST"))


def _from_address() -> str:
    return _clean("EMAIL_FROM_ADDRESS") or _clean("SMTP_USERNAME")


def _from_name() -> str:
    return _clean("EMAIL_FROM_NAME") or "Galactic Builders"


def _send_via_mailjet(*, to: str, subject: str, body: str, from_address: str) -> bool:
    api_key = _clean("MAILJET_API_KEY")
    secret_key = _clean("MAILJET_SECRET_KEY")

    if not secret_key:
        logger.warning("MAILJET_API_KEY is set but MAILJET_SECRET_KEY is missing - skipping send")
        return False

    payload = {
        "Messages": [
            {
                "From": {"Email": from_address, "Name": _from_name()},
                "To": [{"Email": to}],
                "Subject": subject,
                "TextPart": body,
            }
        ]
    }
    basic = base64.b64encode(f"{api_key}:{secret_key}".encode("utf-8")).decode("ascii")
    request = urllib.request.Request(
        MAILJET_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Basic {basic}"},
    )

    try:
        with urllib.request.urlopen(request, timeout=MAIL_TIMEOUT) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 401:
            logger.error(
                "Mailjet rejected the credentials (401). Check MAILJET_API_KEY and "
                "MAILJET_SECRET_KEY - both are required. Response: %s", detail,
            )
        else:
            logger.error("Mailjet API error %s sending to %s: %s", exc.code, to, detail)
        return False
    except urllib.error.URLError as exc:
        logger.error("Mailjet API unreachable sending to %s: %s", to, exc.reason)
        return False
    except Exception:
        logger.exception("Unexpected failure sending to %s via Mailjet", to)
        return False

    # Mailjet answers 200 even when it refuses the message - for example when
    # the sender address has not been validated. Without this check a refused
    # email would be reported as delivered.
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        data = {}
    for message in data.get("Messages", []):
        if str(message.get("Status", "success")).lower() != "success":
            errors = "; ".join(
                str(err.get("ErrorMessage") or err) for err in message.get("Errors", [])
            ) or "unknown reason"
            logger.error(
                "Mailjet accepted the request but refused the message to %s: %s. "
                "Confirm '%s' is validated under Mailjet -> Senders & Domains.",
                to, errors, from_address,
            )
            return False

    logger.info("Email sent to %s via Mailjet: %s", to, subject)
    return True


def _send_via_smtp(*, to: str, subject: str, body: str, from_address: str) -> bool:
    host = _clean("SMTP_HOST")
    port = int(_clean("SMTP_PORT") or 587)
    username = _clean("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    use_tls = (os.environ.get("SMTP_USE_TLS", "true").lower() != "false")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((_from_name(), from_address))
    message["To"] = to
    message.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(message)
        logger.info("Email sent to %s via SMTP: %s", to, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s over SMTP", to)
        return False


def send(*, to: str, subject: str, body: str) -> bool:
    """Best-effort send. Returns True on success, False on any failure or if
    email isn't configured - callers should treat this as "fire and forget",
    never let it block or fail the surrounding request."""
    provider = active_provider()

    if not is_configured():
        logger.info(
            "Email not configured for provider '%s' - skipping email to %s (%s)",
            provider, to, subject,
        )
        return False

    from_address = _from_address()
    if not from_address:
        logger.warning(
            "Email configured but EMAIL_FROM_ADDRESS/SMTP_USERNAME missing - skipping send"
        )
        return False

    if provider == "mailjet":
        return _send_via_mailjet(to=to, subject=subject, body=body, from_address=from_address)
    return _send_via_smtp(to=to, subject=subject, body=body, from_address=from_address)
