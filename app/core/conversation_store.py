"""Holds ConversationState objects keyed by conversation_id.

Two implementations, same interface (get_or_create/exists/save):

- InMemoryConversationStore: process-local, lost on restart. Simple,
  useful for quick local testing.
- DbConversationStore: persists to the conversations/messages tables via
  conversation_repository — survives restarts, is what production should
  use. Both exist so callers (chat_service.py) never need to know which
  one they're talking to.
"""
from __future__ import annotations

import threading
import uuid
from typing import Callable

from app.core.conversation_state import ConversationState


class InMemoryConversationStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._states: dict[str, ConversationState] = {}

    def get_or_create(self, conversation_id: str | None, session_id: str) -> ConversationState:
        with self._lock:
            if conversation_id and conversation_id in self._states:
                return self._states[conversation_id]
            new_id = conversation_id or str(uuid.uuid4())
            state = ConversationState(session_id=session_id, conversation_id=new_id)
            self._states[new_id] = state
            return state

    def exists(self, conversation_id: str) -> bool:
        with self._lock:
            return conversation_id in self._states

    def save(self, state: ConversationState) -> None:
        with self._lock:
            self._states[state.conversation_id] = state


class DbConversationStore:
    """Same interface as InMemoryConversationStore, backed by the
    `conversations` table. Opens and closes its own short-lived session per
    call, matching the pattern used by every other route-facing service in
    this codebase — callers never pass a session in."""

    def __init__(self, session_factory: Callable[[], object]) -> None:
        self._session_factory = session_factory

    def get_or_create(self, conversation_id: str | None, session_id: str) -> ConversationState:
        from app.repositories import conversation_repository

        db_session = self._session_factory()
        try:
            if conversation_id:
                row = conversation_repository.get(db_session, conversation_id)
                if row is not None:
                    return _row_to_state(row)

            new_id = conversation_id or str(uuid.uuid4())
            state = ConversationState(session_id=session_id, conversation_id=new_id)
            conversation_repository.upsert(db_session, state.to_dict())
            db_session.commit()
            return state
        finally:
            db_session.close()

    def exists(self, conversation_id: str) -> bool:
        from app.repositories import conversation_repository

        db_session = self._session_factory()
        try:
            return conversation_repository.exists(db_session, conversation_id)
        finally:
            db_session.close()

    def save(self, state: ConversationState) -> None:
        from app.repositories import conversation_repository

        db_session = self._session_factory()
        try:
            conversation_repository.upsert(db_session, state.to_dict())
            db_session.commit()
        finally:
            db_session.close()


def _row_to_state(row) -> ConversationState:
    return ConversationState.from_dict({
        "session_id": row.session_id,
        "conversation_id": row.id,
        "mode": row.mode,
        "active_flow": row.active_flow,
        "current_step": row.current_step,
        "pending_field": row.pending_field,
        "completed_fields": row.completed_fields,
        "previous_intent": row.previous_intent,
        "last_customer_message": row.last_customer_message,
        "last_bot_response": row.last_bot_response,
        "human_takeover_active": row.human_takeover_active,
        "takeover_agent_id": row.takeover_agent_id,
    })
