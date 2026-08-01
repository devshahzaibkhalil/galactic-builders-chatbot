from datetime import date, timedelta

import pytest

from app.extensions import build_engine, build_session_factory, create_all
from app.models.appointment import AppointmentStatus
from app.services.appointment_service import (
    AppointmentValidationError,
    list_overdue_appointments,
    request_appointment,
)


@pytest.fixture()
def session():
    engine = build_engine("sqlite:///:memory:")
    create_all(engine)
    s = build_session_factory(engine)()
    yield s
    s.close()


def test_valid_callback_request_saved(session):
    appointment = request_appointment(session, {"appointment_type": "callback", "phone": "574-555-0100"})
    assert appointment.id is not None
    assert appointment.status == AppointmentStatus.REQUESTED


def test_invalid_payload_raises_and_does_not_save(session):
    with pytest.raises(AppointmentValidationError):
        request_appointment(session, {"appointment_type": "not_real"})


def test_overdue_appointment_detected(session):
    from app.models.appointment import Appointment, AppointmentType

    past_date = (date.today() - timedelta(days=5)).isoformat()
    overdue = Appointment(
        appointment_type=AppointmentType.CALLBACK, phone="574-555-0100", requested_date=past_date
    )
    future_date = (date.today() + timedelta(days=5)).isoformat()
    upcoming = Appointment(
        appointment_type=AppointmentType.CALLBACK, phone="574-555-0199", requested_date=future_date
    )
    session.add_all([overdue, upcoming])
    session.commit()

    results = list_overdue_appointments(session)
    assert len(results) == 1
    assert results[0].phone == "574-555-0100"
