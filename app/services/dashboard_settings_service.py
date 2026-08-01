"""Reads and updates the dashboard's appearance settings (colors)."""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models.dashboard_setting import (
    DEFAULT_ACCENT_COLOR,
    DEFAULT_PRIMARY_COLOR,
    DEFAULT_ROW_ID,
    DashboardSetting,
)

_HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


class InvalidColorError(ValueError):
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
