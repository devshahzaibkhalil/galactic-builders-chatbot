"""Admin-facing conversation endpoints: view a conversation's state and
transcript, and take over / return to bot. This is the first place
human_takeover.py (built in an earlier phase, unit-tested in isolation)
gets exercised over real HTTP against the real persisted conversation
store.
"""
from __future__ import annotations

from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from app.core import human_takeover
from app.repositories import conversation_repository
from app.security.permissions import PermissionDeniedError, require_permission

admin_conversations_bp = Blueprint("admin_conversations", __name__, url_prefix="/admin/conversations")


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


@admin_conversations_bp.get("/<conversation_id>")
@login_required
@_require("view_assigned_conversations")
def get_conversation(conversation_id: str):
    store = current_app.extensions["conversation_store"]
    if not store.exists(conversation_id):
        return jsonify({"error": "conversation_not_found"}), 404

    state = store.get_or_create(conversation_id, session_id="admin-view")

    db_session = current_app.extensions["db_session_factory"]()
    try:
        messages = conversation_repository.list_messages(db_session, conversation_id)
        transcript = [{"sender_type": m.sender_type, "content": m.content} for m in messages]
    finally:
        db_session.close()

    return jsonify({
        "conversation_id": state.conversation_id,
        "mode": state.mode,
        "active_flow": state.active_flow,
        "pending_field": state.pending_field,
        "completed_fields": state.completed_fields,
        "human_takeover_active": state.human_takeover_active,
        "takeover_agent_id": state.takeover_agent_id,
        "transcript": transcript,
    })


@admin_conversations_bp.post("/<conversation_id>/takeover")
@login_required
@_require("take_over_conversation")
def takeover_conversation(conversation_id: str):
    store = current_app.extensions["conversation_store"]
    if not store.exists(conversation_id):
        return jsonify({"error": "conversation_not_found"}), 404

    state = store.get_or_create(conversation_id, session_id="admin-view")
    human_takeover.take_over(state, agent_id=current_user.id, agent_role=current_user.role)
    store.save(state)

    return jsonify({"mode": state.mode, "human_takeover_active": state.human_takeover_active})


@admin_conversations_bp.post("/<conversation_id>/return-to-bot")
@login_required
@_require("take_over_conversation")
def return_conversation_to_bot(conversation_id: str):
    store = current_app.extensions["conversation_store"]
    if not store.exists(conversation_id):
        return jsonify({"error": "conversation_not_found"}), 404

    state = store.get_or_create(conversation_id, session_id="admin-view")
    human_takeover.return_to_bot(state)
    store.save(state)

    return jsonify({
        "mode": state.mode,
        "human_takeover_active": state.human_takeover_active,
        "pending_field": state.pending_field,
        "active_flow": state.active_flow,
    })


@admin_conversations_bp.post("/<conversation_id>/messages")
@login_required
@_require("reply_to_customer")
def send_admin_message(conversation_id: str):
    """Agent/admin sends a message while in admin_active mode — saved to
    the transcript so the customer's widget can display it."""
    store = current_app.extensions["conversation_store"]
    if not store.exists(conversation_id):
        return jsonify({"error": "conversation_not_found"}), 404

    payload = request.get_json(silent=True) or {}
    content = (payload.get("message") or "").strip()
    if not content:
        return jsonify({"error": "message is required"}), 400

    db_session = current_app.extensions["db_session_factory"]()
    try:
        conversation_repository.append_message(
            db_session, conversation_id=conversation_id, sender_type="admin", content=content
        )
        db_session.commit()
    finally:
        db_session.close()

    return jsonify({"status": "sent"}), 201
