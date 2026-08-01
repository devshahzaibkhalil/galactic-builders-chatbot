"""Admin-facing lead list, annotated with the Opportunity Priority Board
labels and Estimate Readiness percentages computed in lead_scoring_service
(built in an earlier phase, previously only unit-tested against raw dicts).
Sorting/display only — never auto-rejects a lead, per spec 16.5.
"""
from __future__ import annotations

from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import select

from app.models.lead import Lead
from app.security.permissions import PermissionDeniedError, require_permission
from app.services.audit_service import record as record_audit
from app.services.lead_scoring_service import calculate_priority_label, calculate_readiness
from app.services.notification_service import notify_lead_assigned

admin_leads_bp = Blueprint("admin_leads", __name__, url_prefix="/admin/leads")


def _require(action: str):
    def decorator(view_fn):
        @wraps(view_fn)
        def wrapped(*args, **kwargs):
            try:
                require_permission(current_user.role, action)
            except PermissionDeniedError:
                return jsonify({"error": "permission_denied"}), 403
            return view_fn(*args, **kwargs)
        return wrapped
    return decorator


def _lead_to_scoring_dict(lead: Lead) -> dict:
    return {
        "service_key": lead.service_key,
        "project_description": lead.project_description,
        "city": lead.city,
        "state": lead.state,
        "zip_code": lead.zip_code,
        "timeline": lead.timeline,
        "budget_range": lead.budget_range,
        "full_name": lead.full_name,
        "email": lead.email,
        "phone": lead.phone,
        "preferred_contact_method": lead.preferred_contact_method,
        "photo_count": lead.photo_count,
        "safety_flag": lead.safety_flag,
    }


@admin_leads_bp.get("")
@login_required
@_require("view_all_leads")
def list_leads():
    session_factory = current_app.extensions["db_session_factory"]
    session = session_factory()
    try:
        leads = list(session.execute(select(Lead).order_by(Lead.created_at.desc())).scalars())
        results = []
        for lead in leads:
            scoring_input = _lead_to_scoring_dict(lead)
            readiness = calculate_readiness(scoring_input)
            priority = calculate_priority_label(scoring_input)
            results.append({
                "id": lead.id,
                "public_reference": lead.public_reference,
                "service_key": lead.service_key,
                "full_name": lead.full_name,
                "email": lead.email,
                "phone": lead.phone,
                "city": lead.city,
                "status": lead.status.value,
                "readiness_percent": readiness["readiness_percent"],
                "priority_label": priority,
                "conversation_id": lead.conversation_id,
                "assigned_admin_id": lead.assigned_admin_id,
                "created_at": lead.created_at.isoformat(),
            })
    finally:
        session.close()

    return jsonify({"leads": results})


@admin_leads_bp.post("/<lead_id>/assign")
@login_required
@_require("assign_leads")
def assign_lead(lead_id: str):
    payload = request.get_json(silent=True) or {}
    target_admin_id = payload.get("admin_id")
    if not target_admin_id:
        return jsonify({"error": "admin_id is required"}), 400

    session_factory = current_app.extensions["db_session_factory"]
    session = session_factory()
    try:
        lead = session.get(Lead, lead_id)
        if lead is None:
            return jsonify({"error": "lead_not_found"}), 404

        lead.assigned_admin_id = target_admin_id
        notify_lead_assigned(
            session, admin_id=target_admin_id, lead_id=lead.id, public_reference=lead.public_reference
        )
        record_audit(
            session,
            action="lead.assign",
            actor_id=current_user.id,
            actor_role=current_user.role,
            target_type="lead",
            target_id=lead.id,
            metadata={"assigned_admin_id": target_admin_id},
        )
        session.commit()
        result = {"id": lead.id, "assigned_admin_id": lead.assigned_admin_id}
    finally:
        session.close()

    return jsonify(result)
