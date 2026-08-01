"""Renders and sends lead-related emails.

Owns subject-line construction (never includes street address, phone, or
email in the subject — see build_admin_subject) and template rendering.
Actual delivery goes through an injected `transport` callable so this
module has zero SMTP dependency and is fully testable with a fake.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models.lead import Lead

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "emails"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(disabled_extensions=("txt",), default=False),
)


class EmailTransport(Protocol):
    def __call__(self, *, to: str, subject: str, body: str) -> None: ...


def build_admin_subject(lead: Lead) -> str:
    """Never includes full street address, phone, or email — PII stays out
    of the subject line, which is often visible in notification previews."""
    service_label = lead.service_key.replace("_", " ").title()
    if lead.safety_flag:
        return f"Priority Project Request | {service_label} | {lead.city or 'Unknown city'}"
    return f"New {service_label} Lead | {lead.full_name or 'Unnamed'} | {lead.city or 'Unknown city'}"


def render_admin_notification(lead: Lead, dashboard_url: str) -> str:
    template = _env.get_template("admin_lead_notification.txt")
    return template.render(lead=lead, dashboard_url=dashboard_url)


def render_customer_confirmation(lead: Lead) -> str:
    template = _env.get_template("customer_confirmation.txt")
    return template.render(lead=lead)


def send_admin_notification(
    lead: Lead, *, recipient: str, dashboard_url: str, transport: EmailTransport
) -> None:
    transport(to=recipient, subject=build_admin_subject(lead), body=render_admin_notification(lead, dashboard_url))


def send_customer_confirmation(lead: Lead, *, transport: EmailTransport) -> None:
    if not lead.email:
        return
    subject = f"We received your request | {lead.public_reference}"
    transport(to=lead.email, subject=subject, body=render_customer_confirmation(lead))
