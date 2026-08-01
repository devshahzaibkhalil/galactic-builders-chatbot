"""Coordinates a single chat turn: fetch/create state, run it through
ChatEngine, persist state. Routes call only this — they must not touch
ChatEngine, KnowledgeService, or ConversationState directly (see the
strict non-overlapping architecture rules).
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from app.constants.conversation_modes import BOT_ACTIVE
from app.core.chat_engine import ChatEngine
from app.core.conversation_store import InMemoryConversationStore
from app.core.human_takeover import customer_message_display_notice

SessionFactory = Callable[[], Any]


def handle_chat_turn(
    *,
    store: InMemoryConversationStore,
    engine: ChatEngine,
    session_id: str,
    conversation_id: str | None,
    message: str,
    db_session_factory: Optional[SessionFactory] = None,
) -> dict[str, Any]:
    is_new_conversation = not (conversation_id and store.exists(conversation_id))
    state = store.get_or_create(conversation_id, session_id)
    result = engine.process_message(state, message)
    store.save(state)

    if is_new_conversation and db_session_factory is not None:
        _notify_new_conversation(db_session_factory, conversation_id=state.conversation_id)

    if result.handled_by == "fallback_handler" and db_session_factory is not None:
        _persist_unknown_query(db_session_factory, message=message, state=state)

    response_text = result.response_text
    if response_text is None and state.mode != BOT_ACTIVE:
        response_text = customer_message_display_notice()

    if db_session_factory is not None:
        _persist_messages(db_session_factory, conversation_id=state.conversation_id, customer_message=message, bot_response=response_text)

    return {
        "conversation_id": state.conversation_id,
        "response": response_text,
        "mode": state.mode,
        "active_flow": state.active_flow,
        "pending_field": state.pending_field,
        "handled_by": result.handled_by,
    }


def _notify_new_conversation(db_session_factory: SessionFactory, *, conversation_id: str) -> None:
    from app.services.notification_service import notify_new_conversation

    db_session = db_session_factory()
    try:
        notify_new_conversation(db_session, conversation_id=conversation_id)
        db_session.commit()
    finally:
        db_session.close()


def _persist_unknown_query(db_session_factory: SessionFactory, *, message: str, state) -> None:
    from app.services.knowledge_improvement_service import log_unknown_query

    db_session = db_session_factory()
    try:
        log_unknown_query(
            db_session,
            message=message,
            attempted_service_key=state.completed_fields.get("service_key"),
            attempted_intent=state.previous_intent,
            conversation_id=state.conversation_id,
        )
        db_session.commit()
    finally:
        db_session.close()


def _persist_messages(
    db_session_factory: SessionFactory, *, conversation_id: str, customer_message: str, bot_response: str | None
) -> None:
    from app.repositories import conversation_repository

    db_session = db_session_factory()
    try:
        conversation_repository.append_message(
            db_session, conversation_id=conversation_id, sender_type="customer", content=customer_message
        )
        if bot_response:
            conversation_repository.append_message(
                db_session, conversation_id=conversation_id, sender_type="bot", content=bot_response
            )
        db_session.commit()
    finally:
        db_session.close()
