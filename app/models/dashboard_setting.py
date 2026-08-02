"""Admin dashboard appearance settings (colors). Single-row table — there
is exactly one dashboard-wide theme, not per-admin themes, so this is
simpler than a general key-value settings table would be.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base

DEFAULT_ROW_ID = "default"
DEFAULT_PRIMARY_COLOR = "#0d2238"  # navy-900
DEFAULT_ACCENT_COLOR = "#d2a33b"   # gold-500


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DashboardSetting(Base):
    __tablename__ = "dashboard_settings"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=lambda: DEFAULT_ROW_ID)
    primary_color: Mapped[str] = mapped_column(String(7), default=DEFAULT_PRIMARY_COLOR)
    accent_color: Mapped[str] = mapped_column(String(7), default=DEFAULT_ACCENT_COLOR)
    # Overrides the LEAD_NOTIFICATION_EMAIL env var when set — lets a
    # superadmin change where new-lead emails go without a redeploy. NULL
    # means "fall back to the env var" (see dashboard_settings_service).
    lead_notification_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
