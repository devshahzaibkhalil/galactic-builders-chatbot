from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.security.rate_limits import APPOINTMENT_RATE_LIMIT, limiter
from app.services.appointment_service import AppointmentValidationError, request_appointment

appointment_api_bp = Blueprint("appointment_api", __name__, url_prefix="/api/appointments")


@appointment_api_bp.post("")
@limiter.limit(APPOINTMENT_RATE_LIMIT)
def create_appointment():
    payload = request.get_json(silent=True) or {}
    session_factory = current_app.extensions["db_session_factory"]
    session = session_factory()

    try:
        appointment = request_appointment(session, payload)
    except AppointmentValidationError as exc:
        return jsonify({"error": "validation_failed", "fields": exc.errors}), 422
    finally:
        session.close()

    return jsonify({
        "id": appointment.id,
        "appointment_type": appointment.appointment_type.value,
        "status": appointment.status.value,
        "requested_date": appointment.requested_date,
        "time_window": appointment.time_window,
    }), 201
