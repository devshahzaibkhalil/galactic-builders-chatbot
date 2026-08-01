"""In-memory representation of everything the chat engine needs to know
about one conversation. This is the object flow_manager, side_question_
detector, human_takeover, and safety_router all read and mutate — no other
module should carry its own parallel copy of this state.

Persistence (the `conversation_states` DB table) is out of scope for this
phase; to_dict()/from_dict() exist so a repository can serialize this
directly once that table is built.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from app.constants.conversation_modes import BOT_ACTIVE


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class BotStateSnapshot:
    """Captured when handing off to a human, restored on return_to_bot."""
    active_flow: Optional[str]
    current_step: Optional[str]
    pending_field: Optional[str]
    completed_fields: dict[str, Any]


@dataclass
class ConversationState:
    session_id: str
    conversation_id: str

    mode: str = BOT_ACTIVE
    active_flow: Optional[str] = None
    current_step: Optional[str] = None
    pending_field: Optional[str] = None
    completed_fields: dict[str, Any] = field(default_factory=dict)

    previous_intent: Optional[str] = None
    last_customer_message: Optional[str] = None
    last_bot_response: Optional[str] = None

    human_takeover_active: bool = False
    takeover_agent_id: Optional[str] = None
    _bot_snapshot: Optional[BotStateSnapshot] = None

    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def touch(self) -> None:
        self.updated_at = _utcnow()

    def set_pending_field(self, field_name: Optional[str]) -> None:
        self.pending_field = field_name
        self.touch()

    def complete_field(self, field_name: str, value: Any) -> None:
        self.completed_fields[field_name] = value
        self.touch()

    def reopen_field(self, field_name: str) -> None:
        """Used by 'change my email' style commands — clears just one field
        without discarding the others."""
        self.completed_fields.pop(field_name, None)
        self.pending_field = field_name
        self.touch()

    def reset_flow(self) -> None:
        self.active_flow = None
        self.current_step = None
        self.pending_field = None
        self.completed_fields = {}
        self.touch()

    def record_turn(self, customer_message: str, bot_response: Optional[str] = None) -> None:
        self.last_customer_message = customer_message
        if bot_response is not None:
            self.last_bot_response = bot_response
        self.touch()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "mode": self.mode,
            "active_flow": self.active_flow,
            "current_step": self.current_step,
            "pending_field": self.pending_field,
            "completed_fields": dict(self.completed_fields),
            "previous_intent": self.previous_intent,
            "last_customer_message": self.last_customer_message,
            "last_bot_response": self.last_bot_response,
            "human_takeover_active": self.human_takeover_active,
            "takeover_agent_id": self.takeover_agent_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationState":
        state = cls(session_id=data["session_id"], conversation_id=data["conversation_id"])
        state.mode = data.get("mode", BOT_ACTIVE)
        state.active_flow = data.get("active_flow")
        state.current_step = data.get("current_step")
        state.pending_field = data.get("pending_field")
        state.completed_fields = dict(data.get("completed_fields", {}))
        state.previous_intent = data.get("previous_intent")
        state.last_customer_message = data.get("last_customer_message")
        state.last_bot_response = data.get("last_bot_response")
        state.human_takeover_active = data.get("human_takeover_active", False)
        state.takeover_agent_id = data.get("takeover_agent_id")
        return state
