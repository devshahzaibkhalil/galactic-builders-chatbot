import pytest

from app.extensions import build_engine, build_session_factory, create_all
from app.services.lead_service import LeadValidationError, submit_lead
from app.validators.spam_validator import check_spam


def test_honeypot_field_triggers_spam():
    result = check_spam({"honeypot": "filled_in_by_bot", "project_description": "hi"})
    assert not result["valid"]
    assert result["error_code"] == "spam_honeypot_triggered"


def test_excessive_links_triggers_spam():
    desc = "Check http://a.com and http://b.com and http://c.com for reference"
    result = check_spam({"project_description": desc})
    assert not result["valid"]
    assert result["error_code"] == "spam_excessive_links"


def test_normal_description_passes():
    result = check_spam({"project_description": "Replace kitchen cabinets and countertops."})
    assert result["valid"]


VALID_PAYLOAD = {
    "service_key": "kitchen_remodeling",
    "project_description": "Replace cabinets and countertops.",
    "email": "jordan@example.com",
    "phone": "574-555-0100",
    "interest_response": "yes",
    "contact_consent_given": True,
}


@pytest.fixture()
def session():
    engine = build_engine("sqlite:///:memory:")
    create_all(engine)
    s = build_session_factory(engine)()
    yield s
    s.close()


def test_honeypot_blocks_lead_submission(session):
    payload = dict(VALID_PAYLOAD)
    payload["honeypot"] = "bot-filled-this"
    with pytest.raises(LeadValidationError) as exc_info:
        submit_lead(session, payload, queue_email=lambda *a: None)
    assert exc_info.value.errors["spam"] == "spam_honeypot_triggered"
