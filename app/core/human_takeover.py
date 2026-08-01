"""Controls switching a conversation between bot_active, admin_active,
waiting_for_customer, and closed.

Only this module may change ConversationState.mode — chat_engine and
routes call these functions rather than setting `.mode` directly, so the
bot-state snapshot/restore behavior can never be skipped by accident.
"""
from __future__ import annotations

from typing import Optional

from app.constants.conversation_modes import ADMIN_ACTIVE, BOT_ACTIVE, WAITING_FOR_CUSTOMER
from app.core.conversation_state import BotStateSnapshot, ConversationState

ALLOWED_TAKEOVER_ROLES = {"agent", "admin", "superadmin"}


class UnauthorizedTakeoverError(PermissionError):
    pass


def take_over(state: ConversationState, agent_id: str, agent_role: str) -> ConversationState:
    """Authorized staff pauses the bot and takes control of the conversation.

    Preserves the bot's in-progress flow state so it can be restored later.
    """
    if agent_role not in ALLOWED_TAKEOVER_ROLES:
        raise UnauthorizedTakeoverError(f"Role '{agent_role}' may not take over a conversation.")

    if not state.human_takeover_active:
        state._bot_snapshot = BotStateSnapshot(
            active_flow=state.active_flow,
            current_step=state.current_step,
            pending_field=state.pending_field,
            completed_fields=dict(state.completed_fields),
        )

    state.mode = ADMIN_ACTIVE
    state.human_takeover_active = True
    state.takeover_agent_id = agent_id
    state.touch()
    return state


def return_to_bot(state: ConversationState) -> ConversationState:
    """Restores the bot's previous step/pending field exactly as it was
    before the human took over."""
    snapshot: Optional[BotStateSnapshot] = state._bot_snapshot
    if snapshot is not None:
        state.active_flow = snapshot.active_flow
        state.current_step = snapshot.current_step
        state.pending_field = snapshot.pending_field
        state.completed_fields = dict(snapshot.completed_fields)
        state._bot_snapshot = None

    state.mode = BOT_ACTIVE
    state.human_takeover_active = False
    state.takeover_agent_id = None
    state.touch()
    return state


def mark_waiting_for_customer(state: ConversationState) -> ConversationState:
    state.mode = WAITING_FOR_CUSTOMER
    state.touch()
    return state


def customer_message_display_notice() -> str:
    return "You are speaking with the Galactic Builders team."
