from app.core.side_question_detector import MessageKind, detect
from app.validators.email_validator import validate_email


def test_question_while_email_pending_is_side_question():
    result = detect("Do you remodel basements?", pending_field="email")
    assert result.kind == MessageKind.SIDE_QUESTION


def test_valid_email_is_field_answer():
    result = detect("jordan@example.com", pending_field="email", field_validator=validate_email)
    assert result.kind == MessageKind.FIELD_ANSWER


def test_navigation_command_detected_even_with_pending_field():
    result = detect("back", pending_field="email")
    assert result.kind == MessageKind.NAVIGATION_COMMAND
    assert result.command == "back"


def test_change_email_command_detected():
    result = detect("change my email", pending_field="phone")
    assert result.kind == MessageKind.NAVIGATION_COMMAND
    assert result.command == "change_email"


def test_pricing_side_question_during_phone_collection():
    result = detect("How much will this cost?", pending_field="phone")
    assert result.kind == MessageKind.SIDE_QUESTION


def test_garbage_that_isnt_a_question_is_still_field_answer_for_validator_to_reject():
    result = detect("asdf1234", pending_field="email", field_validator=validate_email)
    assert result.kind == MessageKind.FIELD_ANSWER


def test_no_pending_field_defaults_by_question_shape():
    assert detect("What services do you offer?", pending_field=None).kind == MessageKind.SIDE_QUESTION
    assert detect("kitchen remodeling", pending_field=None).kind == MessageKind.FIELD_ANSWER
