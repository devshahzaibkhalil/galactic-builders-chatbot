from app.core.safety_router import check_safety


def test_gas_smell_detected():
    result = check_safety("I smell gas in the kitchen")
    assert result.is_safety_concern
    assert result.message is not None


def test_electrical_fire_detected():
    result = check_safety("There is an electrical fire near the panel")
    assert result.is_safety_concern


def test_cannot_shut_off_water_detected():
    result = check_safety("The pipe burst and I cannot shut off the water")
    assert result.is_safety_concern


def test_normal_message_not_flagged():
    result = check_safety("I'd like a quote for a new deck")
    assert not result.is_safety_concern
    assert result.message is None


def test_message_never_promises_emergency_attendance():
    result = check_safety("Gas smell in my basement")
    assert "will send" not in result.message.lower()
    assert "guarantee" not in result.message.lower()
