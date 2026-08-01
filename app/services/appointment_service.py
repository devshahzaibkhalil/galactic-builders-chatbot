"""Coordinates appointment/callback request creation and the overdue-
follow-up view used by the Contact Window Guard / Follow-Up Desk features.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentType
from app.repositories import appointment_repository
from app.services.notification_service import notify_new_appointment
from app.validators.appointment_validator import validate_appointment


class AppointmentValidationError(ValueError):
    def __init__(self, errors: dict[str, str]):
        super().__init__("Appointment payload failed validation.")
        self.errors = errors


def request_appointment(session: Session, payload: dict[str, Any]) -> Appointment:
    validation = validate_appointment(payload)
    if not validation["valid"]:
        raise AppointmentValidationError(validation["errors"])

    normalized = validation["normalized"]
    appointment = Appointment(
        lead_id=normalized.get("lead_id"),
        conversation_id=normalized.get("conversation_id"),
        appointment_type=AppointmentType(normalized["appointment_type"]),
        full_name=normalized.get("full_name"),
        email=normalized.get("email"),
        phone=normalized.get("phone"),
        requested_date=normalized.get("requested_date"),
        time_window=normalized.get("time_window"),
        customer_timezone=normalized.get("customer_timezone"),
    )
    appointment_repository.insert(session, appointment)
    session.commit()
    notify_new_appointment(
        session, appointment_id=appointment.id, appointment_type=appointment.appointment_type.value
    )
    session.commit()
    return appointment


def list_overdue_appointments(session: Session) -> list[Appointment]:
    return appointment_repository.list_overdue(session)
