from app.validators.interest_response_validator import validate_interest_response


def test_button_yes():
    r = validate_interest_response("yes", from_button=True)
    assert r["valid"] and r["normalized_value"] == "yes"


def test_button_no():
    r = validate_interest_response("no", from_button=True)
    assert r["valid"] and r["normalized_value"] == "no"


def test_typed_variations_map_to_yes():
    for text in ["yes", "y", "yeah", "sure", "continue", "move forward", "Move Forward"]:
        r = validate_interest_response(text)
        assert r["valid"] and r["normalized_value"] == "yes", text


def test_typed_variations_map_to_no():
    for text in ["no", "n", "not now", "stop", "cancel"]:
        r = validate_interest_response(text)
        assert r["valid"] and r["normalized_value"] == "no", text


def test_side_question_is_not_treated_as_yes_or_no():
    r = validate_interest_response("How much will it cost?")
    assert not r["valid"]
    assert r["normalized_value"] is None
    assert r["error_code"] == "unclear_response"


def test_empty_response():
    r = validate_interest_response("   ")
    assert not r["valid"]
    assert r["error_code"] == "empty_response"
