from datetime import date, timedelta

from app.validators.appointment_validator import validate_appointment
from app.validators.date_time_validator import validate_appointment_date, validate_time_window


def test_valid_future_date_accepted():
    tomorrow = (date.today() + timedelta(days=3)).isoformat()
    result = validate_appointment_date(tomorrow)
    assert result["valid"]


def test_past_date_rejected():
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    result = validate_appointment_date(yesterday)
    assert not result["valid"]
    assert result["error_code"] == "date_in_past"


def test_too_far_future_date_rejected():
    far = (date.today() + timedelta(days=200)).isoformat()
    result = validate_appointment_date(far)
    assert not result["valid"]
    assert result["error_code"] == "date_too_far_out"


def test_malformed_date_rejected():
    result = validate_appointment_date("not-a-date")
    assert not result["valid"]
    assert result["error_code"] == "date_invalid_format"


def test_valid_time_windows_accepted():
    for w in ["morning", "afternoon", "evening", "any_time", "Any Time"]:
        result = validate_time_window(w)
        assert result["valid"], w


def test_invalid_time_window_rejected():
    result = validate_time_window("midnight rave")
    assert not result["valid"]


def test_appointment_requires_type():
    result = validate_appointment({"phone": "574-555-0100"})
    assert not result["valid"]
    assert "appointment_type" in result["errors"]


def test_appointment_requires_some_contact_method():
    result = validate_appointment({"appointment_type": "callback"})
    assert not result["valid"]
    assert "contact" in result["errors"]


def test_valid_callback_request():
    result = validate_appointment({"appointment_type": "callback", "phone": "574-555-0100"})
    assert result["valid"]
    assert result["normalized"]["phone"] == "(574) 555-0100"


def test_valid_consultation_with_date_and_window():
    tomorrow = (date.today() + timedelta(days=2)).isoformat()
    result = validate_appointment(
        {
            "appointment_type": "consultation",
            "email": "jordan@example.com",
            "requested_date": tomorrow,
            "time_window": "morning",
        }
    )
    assert result["valid"]
