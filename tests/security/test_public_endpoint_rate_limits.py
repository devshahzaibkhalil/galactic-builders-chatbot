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


def test_chat_message_rate_limited_after_threshold(client):
    statuses = []
    for i in range(70):
        resp = client.post("/api/chat/message", json={"message": f"message {i}", "session_id": "s1"})
        statuses.append(resp.status_code)
    assert 429 in statuses


def test_lead_submission_rate_limited_after_threshold(client):
    statuses = []
    for i in range(15):
        payload = dict(VALID_LEAD_PAYLOAD)
        payload["email"] = f"test{i}@example.com"
        resp = client.post("/api/leads", json=payload)
        statuses.append(resp.status_code)
    assert 429 in statuses


def test_appointment_requests_rate_limited_after_threshold(client):
    statuses = []
    for _ in range(15):
        resp = client.post("/api/appointments", json={"appointment_type": "callback", "phone": "574-555-0100"})
        statuses.append(resp.status_code)
    assert 429 in statuses
