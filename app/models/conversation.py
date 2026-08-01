"""Persisted conversation state, replacing the in-memory placeholder store
described in core/conversation_store.py. Column layout mirrors
ConversationState.to_dict()/from_dict() exactly — those two methods and
this model must be kept in sync.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # == ConversationState.conversation_id
    session_id: Mapped[str] = mapped_column(String(128), index=True)

    mode: Mapped[str] = mapped_column(String(24))
    active_flow: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pending_field: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_fields_json: Mapped[str] = mapped_column(Text, default="{}")

    previous_intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_customer_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_bot_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    human_takeover_active: Mapped[bool] = mapped_column(Boolean, default=False)
    takeover_agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    @property
    def completed_fields(self) -> dict:
        try:
            return json.loads(self.completed_fields_json)
        except (TypeError, ValueError):
            return {}

    @completed_fields.setter
    def completed_fields(self, value: dict) -> None:
        self.completed_fields_json = json.dumps(value, default=str)
