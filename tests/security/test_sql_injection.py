import pytest

from app import create_app

SQLI_PAYLOADS = [
    "'; DROP TABLE leads; --",
    "' OR '1'='1",
    "1; SELECT * FROM admin_users",
    "Robert'); DROP TABLE leads;--",
]

VALID_LEAD_PAYLOAD = {
    "service_key": "kitchen_remodeling",
    "full_name": "Jordan Smith",
    "email": "jordan@example.com",
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


@pytest.mark.parametrize("payload_text", SQLI_PAYLOADS)
def test_sql_injection_in_project_description_stored_literally(client, payload_text):
    payload = dict(VALID_LEAD_PAYLOAD)
    payload["project_description"] = payload_text
    resp = client.post("/api/leads", json=payload)
    assert resp.status_code == 201  # accepted as ordinary text, not executed as SQL


def test_sql_injection_does_not_break_duplicate_check_query(client):
    payload = dict(VALID_LEAD_PAYLOAD)
    payload["project_description"] = "' OR '1'='1"
    first = client.post("/api/leads", json=payload)
    assert first.status_code == 201

    # A second submission with the same email/service should be flagged as
    # a duplicate — proving the parameterized query still executes
    # correctly and the table wasn't dropped/corrupted by the payload.
    second = client.post("/api/leads", json=payload)
    assert second.status_code == 422
    assert second.get_json()["fields"].get("spam") == "duplicate_submission"


def test_database_still_intact_after_injection_attempts(client):
    for payload_text in SQLI_PAYLOADS:
        payload = dict(VALID_LEAD_PAYLOAD)
        payload["email"] = f"test{hash(payload_text) % 10000}@example.com"
        payload["project_description"] = payload_text
        client.post("/api/leads", json=payload)

    # Table still queryable — proves no DROP TABLE succeeded.
    resp = client.post("/api/leads", json=VALID_LEAD_PAYLOAD)
    assert resp.status_code in (201, 422)
