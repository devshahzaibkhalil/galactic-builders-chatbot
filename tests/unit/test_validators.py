from app.validators.email_validator import validate_email
from app.validators.phone_validator import validate_phone
from app.validators.zip_validator import validate_zip


def test_valid_email():
    r = validate_email("Jordan@Example.com")
    assert r["valid"]
    assert r["normalized_value"] == "jordan@example.com"


def test_invalid_email_missing_at():
    r = validate_email("not-an-email")
    assert not r["valid"]
    assert r["error_code"] == "email_invalid_format"


def test_email_header_injection_rejected():
    r = validate_email("jordan@example.com\r\nBcc: attacker@evil.com")
    assert not r["valid"]
    assert r["error_code"] == "email_header_injection"


def test_valid_phone_variants():
    for raw in ["5745550100", "(574) 555-0100", "1-574-555-0100"]:
        r = validate_phone(raw)
        assert r["valid"], raw
        assert r["normalized_value"] == "(574) 555-0100"


def test_invalid_phone_too_short():
    r = validate_phone("12345")
    assert not r["valid"]
    assert r["error_code"] == "phone_invalid_length"


def test_valid_zip():
    r = validate_zip("46601")
    assert r["valid"]
    assert r["normalized_value"] == "46601"


def test_valid_zip_plus4():
    r = validate_zip("46601-1234")
    assert r["valid"]
    assert r["normalized_value"] == "46601"


def test_invalid_zip():
    r = validate_zip("ABCDE")
    assert not r["valid"]
    assert r["error_code"] == "zip_invalid_format"
