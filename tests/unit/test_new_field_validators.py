from app.validators.budget_validator import validate_budget_range
from app.validators.contact_method_validator import validate_contact_method
from app.validators.header_injection_validator import validate_no_header_injection
from app.validators.name_validator import validate_name
from app.validators.property_validator import validate_property_type
from app.validators.sensitive_data_validator import validate_no_sensitive_data
from app.validators.url_validator import validate_url
from app.validators.username_validator import validate_username


def test_valid_name_accepted():
    r = validate_name("Jordan O'Malley-Smith")
    assert r["valid"]


def test_name_with_numbers_rejected():
    r = validate_name("Jordan123")
    assert not r["valid"]


def test_name_repeated_chars_rejected():
    r = validate_name("aaaaaaaa")
    assert not r["valid"]


def test_empty_name_rejected():
    r = validate_name("")
    assert not r["valid"]
    assert r["error_code"] == "name_required"


def test_valid_budget_ranges():
    for v in ["under_5000", "5000-10000", "50000 plus", "NOT_SURE_YET"]:
        assert validate_budget_range(v)["valid"], v


def test_invalid_budget_range():
    assert not validate_budget_range("a million dollars")["valid"]


def test_valid_property_types():
    for v in ["single_family_home", "Condo", "multi-family"]:
        assert validate_property_type(v)["valid"], v


def test_invalid_property_type():
    assert not validate_property_type("spaceship")["valid"]


def test_valid_contact_methods():
    for v in ["email", "Phone", "TEXT"]:
        assert validate_contact_method(v)["valid"], v


def test_invalid_contact_method():
    assert not validate_contact_method("carrier pigeon")["valid"]


def test_valid_url_with_scheme():
    r = validate_url("https://galacticbuilldersllc.com")
    assert r["valid"]


def test_valid_url_without_scheme_gets_https_added():
    r = validate_url("galacticbuilldersllc.com")
    assert r["valid"]
    assert r["normalized_value"].startswith("https://")


def test_invalid_url_rejected():
    assert not validate_url("not a url at all")["valid"]


def test_valid_username():
    r = validate_username("jordan_smith")
    assert r["valid"]
    assert r["normalized_value"] == "jordan_smith"


def test_reserved_username_rejected():
    assert not validate_username("admin")["valid"]


def test_too_short_username_rejected():
    assert not validate_username("ab")["valid"]


def test_header_injection_crlf_rejected():
    r = validate_no_header_injection("Hello\r\nBcc: attacker@evil.com")
    assert not r["valid"]


def test_header_injection_header_like_line_rejected():
    r = validate_no_header_injection("Subject: hijacked message")
    assert not r["valid"]


def test_header_injection_normal_text_accepted():
    r = validate_no_header_injection("Just a normal project description.")
    assert r["valid"]


def test_ssn_detected_in_free_text():
    r = validate_no_sensitive_data("My SSN is 123-45-6789 if needed")
    assert not r["valid"]
    assert r["error_code"] == "sensitive_data_ssn_detected"


def test_valid_credit_card_number_detected():
    # 4111111111111111 is a well-known Luhn-valid test Visa number.
    r = validate_no_sensitive_data("Card number 4111 1111 1111 1111")
    assert not r["valid"]
    assert r["error_code"] == "sensitive_data_card_detected"


def test_random_long_digit_string_that_fails_luhn_not_flagged():
    r = validate_no_sensitive_data("Order number 1234567890123456")
    assert r["valid"]


def test_normal_project_description_passes():
    r = validate_no_sensitive_data("Replace kitchen cabinets and countertops, about 200 sq ft.")
    assert r["valid"]
