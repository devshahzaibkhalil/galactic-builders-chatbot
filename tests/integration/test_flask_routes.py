import pytest

from app import create_app


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_frame_ancestors_header_present_and_not_wildcard(client):
    resp = client.get("/health")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "frame-ancestors" in csp
    assert "*" not in csp
    assert "galacticbuilldersllc.com" in csp


def test_chat_message_requires_message_field(client):
    resp = client.post("/api/chat/message", json={})
    assert resp.status_code == 400


def test_chat_flow_progresses_across_multiple_requests(client):
    r1 = client.post("/api/chat/message", json={"message": "I want a kitchen remodel", "session_id": "s1"})
    assert r1.status_code == 200
    body1 = r1.get_json()
    conversation_id = body1["conversation_id"]
    assert "kitchen" in body1["response"].lower()

    # No active flow started yet by the FAQ answer alone — this confirms the
    # conversation_id round-trips and state persists across requests.
    r2 = client.post(
        "/api/chat/message",
        json={"message": "gas smell in the kitchen", "conversation_id": conversation_id, "session_id": "s1"},
    )
    assert r2.status_code == 200
    body2 = r2.get_json()
    assert body2["handled_by"] == "safety_router"
    assert body2["conversation_id"] == conversation_id


def test_lead_submission_via_api_end_to_end(client):
    payload = {
        "service_key": "kitchen_remodeling",
        "project_description": "Replace cabinets and countertops.",
        "city": "South Bend",
        "state": "IN",
        "zip_code": "46601",
        "full_name": "Jordan Smith",
        "email": "jordan@example.com",
        "phone": "574-555-0100",
        "preferred_contact_method": "email",
        "interest_response": "yes",
        "contact_consent_given": True,
    }
    resp = client.post("/api/leads", json=payload)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["public_reference"].startswith("GB-")
    assert body["status"] == "new"


def test_lead_submission_rejects_invalid_email(client):
    payload = {
        "service_key": "kitchen_remodeling",
        "project_description": "Replace cabinets.",
        "email": "not-an-email",
        "phone": "574-555-0100",
        "interest_response": "yes",
        "contact_consent_given": True,
    }
    resp = client.post("/api/leads", json=payload)
    assert resp.status_code == 422
    assert "email" in resp.get_json()["fields"]


def test_lead_submission_requires_interest_confirmed(client):
    payload = {
        "service_key": "kitchen_remodeling",
        "project_description": "Replace cabinets.",
        "email": "jordan@example.com",
        "phone": "574-555-0100",
        "interest_response": "no",
        "contact_consent_given": True,
    }
    resp = client.post("/api/leads", json=payload)
    assert resp.status_code in (409, 422)
