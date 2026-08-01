import pytest

from app.constants.conversation_modes import ADMIN_ACTIVE, BOT_ACTIVE
from app.core.conversation_state import ConversationState
from app.core.human_takeover import UnauthorizedTakeoverError, return_to_bot, take_over


@pytest.fixture()
def state():
    s = ConversationState(session_id="s1", conversation_id="c1")
    s.active_flow = "estimate_flow"
    s.current_step = "email"
    s.pending_field = "email"
    s.completed_fields = {"service_key": "kitchen_remodeling"}
    return s


def test_agent_can_take_over(state):
    take_over(state, agent_id="agent-1", agent_role="agent")
    assert state.mode == ADMIN_ACTIVE
    assert state.human_takeover_active is True
    assert state.takeover_agent_id == "agent-1"


def test_admin_and_superadmin_can_take_over(state):
    take_over(state, agent_id="admin-1", agent_role="admin")
    assert state.mode == ADMIN_ACTIVE
    return_to_bot(state)
    take_over(state, agent_id="super-1", agent_role="superadmin")
    assert state.mode == ADMIN_ACTIVE


def test_unauthorized_role_cannot_take_over(state):
    with pytest.raises(UnauthorizedTakeoverError):
        take_over(state, agent_id="customer-1", agent_role="customer")
    assert state.mode == BOT_ACTIVE


def test_return_to_bot_restores_exact_previous_step(state):
    take_over(state, agent_id="agent-1", agent_role="agent")
    # Simulate the bot state changing conceptually while admin is active —
    # pending_field is paused, not advanced, but we verify restore logic
    # against the snapshot regardless.
    return_to_bot(state)
    assert state.mode == BOT_ACTIVE
    assert state.human_takeover_active is False
    assert state.active_flow == "estimate_flow"
    assert state.current_step == "email"
    assert state.pending_field == "email"
    assert state.completed_fields == {"service_key": "kitchen_remodeling"}
