from pathlib import Path

import pytest

from app.constants.conversation_modes import ADMIN_ACTIVE, BOT_ACTIVE
from app.core.chat_engine import ChatEngine
from app.core.conversation_state import ConversationState
from app.core.flow_manager import FlowDefinition, FlowManager, FlowStep
from app.services.knowledge_service import KnowledgeService

FAQ_ROOT = Path(__file__).resolve().parents[2] / "app" / "data" / "faqs"

ESTIMATE_FLOW = FlowDefinition(
    name="estimate_flow",
    steps=[
        FlowStep("service_key", "Which service do you need?"),
        FlowStep("project_description", "Tell us about the project."),
        FlowStep("email", "What email address should the team use?"),
        FlowStep("phone", "What phone number should the team use?"),
    ],
)


@pytest.fixture()
def knowledge_service():
    ks = KnowledgeService(faq_root=FAQ_ROOT)
    ks.load(strict=True)
    return ks


@pytest.fixture()
def engine(knowledge_service):
    return ChatEngine(knowledge_service, FlowManager(ESTIMATE_FLOW))


@pytest.fixture()
def state():
    return ConversationState(session_id="s1", conversation_id="c1")


def test_safety_overrides_everything_even_mid_flow(engine, state):
    engine.flow_manager.start(state)
    state.pending_field = "email"
    result = engine.process_message(state, "I smell gas in my kitchen")
    assert result.handled_by == "safety_router"
    assert "emergency" in result.response_text.lower() or "danger" in result.response_text.lower()
    # Flow position untouched by the safety interrupt.
    assert state.pending_field == "email"


def test_human_takeover_suppresses_bot_response(engine, state):
    state.mode = ADMIN_ACTIVE
    result = engine.process_message(state, "What's my project status?")
    assert result.response_text is None
    assert result.handled_by == "human_takeover"


def test_side_question_during_email_collection_answers_and_repeats_prompt(engine, state):
    engine.flow_manager.start(state)
    state.completed_fields["service_key"] = "basement_remodeling"
    state.pending_field = "email"
    state.current_step = "email"

    result = engine.process_message(state, "Do you remodel basements?")
    assert result.handled_by == "side_question_detector"
    assert "basement" in result.response_text.lower()
    assert "email" in result.response_text.lower()
    # Did not advance the flow.
    assert state.pending_field == "email"
    assert "email" not in state.completed_fields


def test_invalid_email_shows_validation_error_not_side_question(engine, state):
    state.pending_field = "email"
    state.current_step = "email"
    result = engine.process_message(state, "not-an-email")
    assert result.handled_by == "field_validator:invalid"
    assert "valid email" in result.response_text.lower()


def test_valid_field_answer_advances_flow(engine, state):
    engine.flow_manager.start(state)
    state.pending_field = "email"
    state.current_step = "email"
    result = engine.process_message(state, "jordan@example.com")
    assert result.handled_by == "flow_manager:field_answer"
    assert state.completed_fields["email"] == "jordan@example.com"
    assert state.pending_field == "phone"


def test_exact_service_match_with_no_active_flow(engine, state):
    result = engine.process_message(state, "I want to remodel my kitchen")
    assert result.handled_by == "intent_router:exact_match"
    assert "kitchen" in result.response_text.lower()


def test_low_confidence_fallback_for_unrelated_message(engine, state):
    result = engine.process_message(state, "asdkfj qwoeiru zzz nonsense")
    assert result.handled_by == "fallback_handler"
    assert "team member" in result.response_text.lower() or "rephrase" in result.response_text.lower()

def test_navigation_command_change_email_preserves_other_fields(engine, state):
    engine.flow_manager.start(state)
    state.completed_fields = {"service_key": "roof_repair", "project_description": "Leak"}
    state.pending_field = "email"
    state.current_step = "email"
    result = engine.process_message(state, "change my email")
    assert result.handled_by == "flow_manager:navigation_command"
    assert state.pending_field == "email"
    assert state.completed_fields["service_key"] == "roof_repair"
