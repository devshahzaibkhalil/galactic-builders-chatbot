"""Reads and updates the dashboard's appearance settings (colors) and the
lead-notification recipient email."""
from __future__ import annotations

import os
import re

from sqlalchemy.orm import Session

from app.models.dashboard_setting import (
    DEFAULT_ACCENT_COLOR,
    DEFAULT_PRIMARY_COLOR,
    DEFAULT_ROW_ID,
    DashboardSetting,
)
from app.validators.email_validator import validate_email

_HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


class InvalidColorError(ValueError):
    pass


class InvalidNotificationEmailError(ValueError):
    pass


def get_theme(session: Session) -> DashboardSetting:
    setting = session.get(DashboardSetting, DEFAULT_ROW_ID)
    if setting is None:
        setting = DashboardSetting(
            id=DEFAULT_ROW_ID, primary_color=DEFAULT_PRIMARY_COLOR, accent_color=DEFAULT_ACCENT_COLOR
        )
        session.add(setting)
        session.flush()
    return setting


def update_theme(session: Session, *, primary_color: str, accent_color: str) -> DashboardSetting:
    for value in (primary_color, accent_color):
        if not _HEX_COLOR_PATTERN.fullmatch(value):
            raise InvalidColorError(f"'{value}' is not a valid hex color (expected format #RRGGBB).")

    setting = get_theme(session)
    setting.primary_color = primary_color
    setting.accent_color = accent_color
    return setting


def reset_theme(session: Session) -> DashboardSetting:
    setting = get_theme(session)
    setting.primary_color = DEFAULT_PRIMARY_COLOR
    setting.accent_color = DEFAULT_ACCENT_COLOR
    return setting


def get_lead_notification_email(session: Session) -> str | None:
    """The address that broadcast admin notifications (new lead, new
    conversation, etc.) are emailed to. A value saved in the dashboard
    (DB) always wins; otherwise falls back to the LEAD_NOTIFICATION_EMAIL
    env var so existing deployments keep working unchanged."""
    setting = get_theme(session)
    if setting.lead_notification_email:
        return setting.lead_notification_email
    return os.environ.get("LEAD_NOTIFICATION_EMAIL") or None


def get_lead_notification_email_source(session: Session) -> dict:
    """Used by the settings page: the effective address plus whether it
    came from the dashboard override or the env var default."""
    setting = get_theme(session)
    if setting.lead_notification_email:
        return {"email": setting.lead_notification_email, "source": "dashboard"}
    env_value = os.environ.get("LEAD_NOTIFICATION_EMAIL") or None
    return {"email": env_value, "source": "env"}


def update_lead_notification_email(session: Session, raw_email: str | None) -> DashboardSetting:
    """Pass an empty string / None to clear the override and fall back to
    the env var again."""
    setting = get_theme(session)
    if raw_email is None or not raw_email.strip():
        setting.lead_notification_email = None
        return setting

    result = validate_email(raw_email)
    if not result["valid"]:
        raise InvalidNotificationEmailError(result["message"] or "Invalid email address.")

    setting.lead_notification_email = result["normalized_value"]
    return setting
