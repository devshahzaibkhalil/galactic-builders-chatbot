"""Contact Window Guard (spec 16.6).

Prevents automatic non-urgent messages from going out during a customer's
quiet hours, and marks overdue follow-ups. This module makes the decision;
it does not send anything itself (that's email_service/notification_service).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Literal, Optional
from zoneinfo import ZoneInfo

TimeWindow = Literal["morning", "afternoon", "evening", "any_time"]

_WINDOW_HOURS: dict[str, tuple[time, time]] = {
    "morning": (time(8, 0), time(12, 0)),
    "afternoon": (time(12, 0), time(17, 0)),
    "evening": (time(17, 0), time(20, 0)),
}
QUIET_HOURS = (time(20, 0), time(8, 0))  # 8pm - 8am, wraps midnight


@dataclass
class ContactWindowResult:
    is_quiet_hours: bool
    within_preferred_window: Optional[bool]  # None if no preference given
    customer_local_time: datetime


def _in_quiet_hours(local_time: time) -> bool:
    start, end = QUIET_HOURS
    # Wraps midnight: quiet if local_time >= 20:00 OR local_time < 08:00.
    return local_time >= start or local_time < end


def evaluate_contact_window(
    *, customer_timezone: str, preferred_window: Optional[TimeWindow] = None, now_utc: Optional[datetime] = None
) -> ContactWindowResult:
    now_utc = now_utc or datetime.now(ZoneInfo("UTC"))
    local_dt = now_utc.astimezone(ZoneInfo(customer_timezone))
    local_time = local_dt.time()

    quiet = _in_quiet_hours(local_time)

    within_preferred = None
    if preferred_window and preferred_window != "any_time":
        bounds = _WINDOW_HOURS.get(preferred_window)
        within_preferred = bool(bounds and bounds[0] <= local_time < bounds[1])

    return ContactWindowResult(
        is_quiet_hours=quiet, within_preferred_window=within_preferred, customer_local_time=local_dt
    )


def may_send_non_urgent_message(*, customer_timezone: str, now_utc: Optional[datetime] = None) -> bool:
    """Automatic non-urgent messages (reminders, nudges) should be
    suppressed during quiet hours. Urgent/safety messages are never gated
    by this — see safety_router.py, which bypasses this entirely."""
    result = evaluate_contact_window(customer_timezone=customer_timezone, now_utc=now_utc)
    return not result.is_quiet_hours
