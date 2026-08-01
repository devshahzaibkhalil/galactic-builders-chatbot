from __future__ import annotations

import uuid

from flask import Blueprint, current_app, jsonify, request

from app.core.chat_engine import ChatEngine
from app.security.rate_limits import CHAT_MESSAGE_RATE_LIMIT, BOOKMARK_RATE_LIMIT, limiter
from app.services.chat_service import handle_chat_turn
from app.services.conversation_resume_service import (
    BookmarkExpiredError,
    BookmarkInvalidError,
    IdentityMismatchError,
    create_bookmark_token,
    resolve_bookmark_token,
)

chat_api_bp = Blueprint("chat_api", __name__, url_prefix="/api/chat")


@chat_api_bp.post("/message")
@limiter.limit(CHAT_MESSAGE_RATE_LIMIT)
def post_message():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    conversation_id = payload.get("conversation_id")
    session_id = payload.get("session_id") or request.cookies.get("session_id") or str(uuid.uuid4())

    if not message:
        return jsonify({"error": "message is required"}), 400
    if len(message) > 4000:
        return jsonify({"error": "message is too long"}), 400

    engine = ChatEngine(
        current_app.extensions["knowledge_service"],
        current_app.extensions["flow_manager"],
    )
    result = handle_chat_turn(
        store=current_app.extensions["conversation_store"],
        engine=engine,
        session_id=session_id,
        conversation_id=conversation_id,
        message=message,
        db_session_factory=current_app.extensions["db_session_factory"],
    )
    return jsonify(result)


@chat_api_bp.post("/bookmark")
@limiter.limit(BOOKMARK_RATE_LIMIT)
def create_bookmark():
    """Conversation Bookmark: lets the customer save progress and resume
    later. contact_value must be an email or phone already given earlier in
    this conversation — we don't collect anything new just for this."""
    payload = request.get_json(silent=True) or {}
    conversation_id = payload.get("conversation_id")
    contact_value = payload.get("contact_value")

    if not conversation_id or not contact_value:
        return jsonify({"error": "conversation_id and contact_value are required"}), 400

    store = current_app.extensions["conversation_store"]
    if not store.exists(conversation_id):
        return jsonify({"error": "conversation_not_found"}), 404
    state = store.get_or_create(conversation_id, session_id="bookmark-lookup")

    token = create_bookmark_token(
        conversation_id=conversation_id,
        contact_value=contact_value,
        secret_key=current_app.config["SECRET_KEY"],
    )
    return jsonify({"bookmark_token": token})


@chat_api_bp.post("/resume")
@limiter.limit(BOOKMARK_RATE_LIMIT)
def resume_bookmark():
    payload = request.get_json(silent=True) or {}
    token = payload.get("bookmark_token")
    contact_value = payload.get("contact_value")

    if not token or not contact_value:
        return jsonify({"error": "bookmark_token and contact_value are required"}), 400

    try:
        conversation_id = resolve_bookmark_token(
            token,
            provided_contact_value=contact_value,
            secret_key=current_app.config["SECRET_KEY"],
        )
    except BookmarkExpiredError:
        return jsonify({"error": "bookmark_expired", "message": "This saved link has expired."}), 410
    except (BookmarkInvalidError, IdentityMismatchError):
        # Deliberately the same generic response for both — don't let a
        # would-be attacker distinguish "bad token" from "wrong identity".
        return jsonify({"error": "bookmark_invalid", "message": "We couldn't verify this saved link."}), 401

    store = current_app.extensions["conversation_store"]
    if not store.exists(conversation_id):
        # Token was valid but the in-memory conversation no longer exists
        # (e.g. server restarted) — this in-memory store is a placeholder
        # for the real conversation_states table; once that exists this
        # branch goes away.
        return jsonify({"error": "bookmark_invalid", "message": "We couldn't verify this saved link."}), 401
    state = store.get_or_create(conversation_id, session_id="resumed")
    return jsonify({
        "conversation_id": state.conversation_id,
        "mode": state.mode,
        "active_flow": state.active_flow,
        "pending_field": state.pending_field,
        "completed_fields": state.completed_fields,
    })
