import pytest

from app import create_app

VALID_LEAD_PAYLOAD = {
    "service_key": "kitchen_remodeling",
    "project_description": "Replace cabinets.",
    "full_name": "Jordan Smith",
    "phone": "574-555-0100",
    "interest_response": "yes",
    "contact_consent_given": True,
}


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def test_crlf_in_email_rejected():
    from app.validators.email_validator import validate_email

    result = validate_email("jordan@example.com\r\nBcc: attacker@evil.com")
    assert not result["valid"]
    assert result["error_code"] == "email_header_injection"


def test_lead_api_rejects_header_injection_email(client):
    payload = dict(VALID_LEAD_PAYLOAD)
    payload["email"] = "jordan@example.com\r\nBcc: attacker@evil.com"
    resp = client.post("/api/leads", json=payload)
    assert resp.status_code == 422
    assert resp.get_json()["fields"].get("email")


def test_newline_only_injection_attempt_rejected():
    from app.validators.email_validator import validate_email

    result = validate_email("jordan@example.com\nSubject: hijacked")
    assert not result["valid"]
    assert result["error_code"] == "email_header_injection"


def test_normal_email_with_plus_addressing_still_accepted():
    from app.validators.email_validator import validate_email

    result = validate_email("jordan+leads@example.com")
    assert result["valid"]
