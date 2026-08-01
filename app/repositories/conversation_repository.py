from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message


def get(session: Session, conversation_id: str) -> Conversation | None:
    return session.get(Conversation, conversation_id)


def exists(session: Session, conversation_id: str) -> bool:
    return get(session, conversation_id) is not None


def upsert(session: Session, conversation_data: dict) -> Conversation:
    existing = get(session, conversation_data["conversation_id"])
    if existing is None:
        existing = Conversation(id=conversation_data["conversation_id"])
        session.add(existing)

    existing.session_id = conversation_data["session_id"]
    existing.mode = conversation_data["mode"]
    existing.active_flow = conversation_data["active_flow"]
    existing.current_step = conversation_data["current_step"]
    existing.pending_field = conversation_data["pending_field"]
    existing.completed_fields = conversation_data["completed_fields"]
    existing.previous_intent = conversation_data["previous_intent"]
    existing.last_customer_message = conversation_data["last_customer_message"]
    existing.last_bot_response = conversation_data["last_bot_response"]
    existing.human_takeover_active = conversation_data["human_takeover_active"]
    existing.takeover_agent_id = conversation_data["takeover_agent_id"]

    session.flush()
    return existing


def append_message(session: Session, *, conversation_id: str, sender_type: str, content: str) -> Message:
    message = Message(conversation_id=conversation_id, sender_type=sender_type, content=content)
    session.add(message)
    session.flush()
    return message


def list_messages(session: Session, conversation_id: str) -> list[Message]:
    stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    return list(session.execute(stmt).scalars())
