from app.security.redaction import redact, redact_dict


def test_redacts_email():
    text = "Lead submitted with email jordan@example.com for follow-up"
    result = redact(text)
    assert "jordan@example.com" not in result
    assert "[REDACTED]" in result


def test_redacts_phone():
    text = "Called customer at (574) 555-0100 this morning"
    result = redact(text)
    assert "555-0100" not in result


def test_redacts_ssn():
    text = "SSN on file: 123-45-6789"
    result = redact(text)
    assert "123-45-6789" not in result


def test_leaves_non_sensitive_text_untouched():
    text = "Kitchen remodel lead created successfully"
    assert redact(text) == text


def test_empty_string_handled():
    assert redact("") == ""


def test_redact_dict_by_key_name():
    data = {"email": "jordan@example.com", "service_key": "kitchen_remodeling"}
    result = redact_dict(data)
    assert result["email"] == "[REDACTED]"
    assert result["service_key"] == "kitchen_remodeling"


def test_redact_dict_recurses_into_nested_dicts():
    data = {"lead": {"phone": "574-555-0100", "city": "South Bend"}}
    result = redact_dict(data)
    assert result["lead"]["phone"] == "[REDACTED]"
    assert result["lead"]["city"] == "South Bend"


def test_redact_dict_also_pattern_matches_string_values_not_flagged_by_key():
    data = {"notes": "reach out at jordan@example.com"}
    result = redact_dict(data)
    assert "jordan@example.com" not in result["notes"]
