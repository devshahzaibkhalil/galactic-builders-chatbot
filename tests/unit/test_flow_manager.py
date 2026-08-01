import pytest

from app.core.conversation_state import ConversationState
from app.core.flow_manager import FlowDefinition, FlowManager, FlowStep

SIMPLE_FLOW = FlowDefinition(
    name="estimate_flow",
    steps=[
        FlowStep("service_key", "Which service do you need?"),
        FlowStep("project_description", "Tell us about the project."),
        FlowStep("email", "What email should we use?"),
        FlowStep("phone", "What phone number should we use?"),
        FlowStep("photo_upload", "Any photos to share?", optional=True),
    ],
)


@pytest.fixture()
def state():
    return ConversationState(session_id="s1", conversation_id="c1")


@pytest.fixture()
def manager():
    return FlowManager(SIMPLE_FLOW)


def test_start_sets_first_pending_field(manager, state):
    step = manager.start(state)
    assert step.field_name == "service_key"
    assert state.pending_field == "service_key"
    assert state.active_flow == "estimate_flow"


def test_submitting_answers_advances_through_all_steps(manager, state):
    manager.start(state)
    manager.submit_field_answer(state, "kitchen_remodeling")
    assert state.pending_field == "project_description"

    manager.submit_field_answer(state, "Replace cabinets")
    assert state.pending_field == "email"

    manager.submit_field_answer(state, "jordan@example.com")
    assert state.pending_field == "phone"

    manager.submit_field_answer(state, "5745550100")
    assert state.pending_field == "photo_upload"

    next_step = manager.submit_field_answer(state, None)
    assert next_step is None
    assert state.pending_field is None


def test_changing_email_preserves_other_completed_fields(manager, state):
    manager.start(state)
    manager.submit_field_answer(state, "kitchen_remodeling")
    manager.submit_field_answer(state, "Replace cabinets")
    manager.submit_field_answer(state, "wrong@example.com")
    manager.submit_field_answer(state, "5745550100")

    assert state.completed_fields["service_key"] == "kitchen_remodeling"
    assert state.completed_fields["email"] == "wrong@example.com"

    manager.handle_navigation_command(state, "change_email")
    assert state.pending_field == "email"
    assert "email" not in state.completed_fields
    # Other fields untouched.
    assert state.completed_fields["service_key"] == "kitchen_remodeling"
    assert state.completed_fields["phone"] == "5745550100"

    manager.submit_field_answer(state, "correct@example.com")
    assert state.completed_fields["email"] == "correct@example.com"


def test_back_command_reopens_previous_field(manager, state):
    manager.start(state)
    manager.submit_field_answer(state, "kitchen_remodeling")
    manager.submit_field_answer(state, "Replace cabinets")
    # Now pending_field == "email"; go back.
    step = manager.handle_navigation_command(state, "back")
    assert step.field_name == "project_description"
    assert state.pending_field == "project_description"
    assert "project_description" not in state.completed_fields
    # service_key still preserved.
    assert state.completed_fields["service_key"] == "kitchen_remodeling"


def test_start_over_clears_everything(manager, state):
    manager.start(state)
    manager.submit_field_answer(state, "kitchen_remodeling")
    manager.handle_navigation_command(state, "start_over")
    assert state.completed_fields == {}
    assert state.pending_field == "service_key"


def test_skip_only_works_on_optional_fields(manager, state):
    manager.start(state)
    manager.submit_field_answer(state, "kitchen_remodeling")
    manager.submit_field_answer(state, "Replace cabinets")
    # email is required — skip should be a no-op (returns same step).
    step = manager.handle_navigation_command(state, "skip")
    assert step.field_name == "email"
    assert state.pending_field == "email"


def test_skip_optional_photo_upload_completes_flow(manager, state):
    manager.start(state)
    manager.submit_field_answer(state, "kitchen_remodeling")
    manager.submit_field_answer(state, "Replace cabinets")
    manager.submit_field_answer(state, "jordan@example.com")
    manager.submit_field_answer(state, "5745550100")
    result = manager.handle_navigation_command(state, "skip")
    assert result is None
    assert state.pending_field is None
