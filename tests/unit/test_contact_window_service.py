from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.contact_window_service import evaluate_contact_window, may_send_non_urgent_message

EASTERN = "America/New_York"


def test_quiet_hours_detected_late_at_night():
    # 11 PM Eastern
    now_utc = datetime(2026, 1, 15, 4, 0, tzinfo=ZoneInfo("UTC"))  # 11 PM ET the prior day
    result = evaluate_contact_window(customer_timezone=EASTERN, now_utc=now_utc)
    assert result.is_quiet_hours


def test_daytime_is_not_quiet_hours():
    # 2 PM Eastern -> 19:00 UTC (winter, EST = UTC-5)
    now_utc = datetime(2026, 1, 15, 19, 0, tzinfo=ZoneInfo("UTC"))
    result = evaluate_contact_window(customer_timezone=EASTERN, now_utc=now_utc)
    assert not result.is_quiet_hours


def test_may_send_non_urgent_message_false_during_quiet_hours():
    now_utc = datetime(2026, 1, 15, 4, 0, tzinfo=ZoneInfo("UTC"))
    assert not may_send_non_urgent_message(customer_timezone=EASTERN, now_utc=now_utc)


def test_may_send_non_urgent_message_true_during_day():
    now_utc = datetime(2026, 1, 15, 19, 0, tzinfo=ZoneInfo("UTC"))
    assert may_send_non_urgent_message(customer_timezone=EASTERN, now_utc=now_utc)


def test_preferred_window_match_detected():
    # 10 AM Eastern -> 15:00 UTC (winter)
    now_utc = datetime(2026, 1, 15, 15, 0, tzinfo=ZoneInfo("UTC"))
    result = evaluate_contact_window(customer_timezone=EASTERN, preferred_window="morning", now_utc=now_utc)
    assert result.within_preferred_window is True


def test_preferred_window_mismatch_detected():
    now_utc = datetime(2026, 1, 15, 15, 0, tzinfo=ZoneInfo("UTC"))  # 10 AM ET
    result = evaluate_contact_window(customer_timezone=EASTERN, preferred_window="evening", now_utc=now_utc)
    assert result.within_preferred_window is False


def test_any_time_preference_returns_none_for_within_window():
    now_utc = datetime(2026, 1, 15, 15, 0, tzinfo=ZoneInfo("UTC"))
    result = evaluate_contact_window(customer_timezone=EASTERN, preferred_window="any_time", now_utc=now_utc)
    assert result.within_preferred_window is None
