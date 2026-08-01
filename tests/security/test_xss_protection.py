import pytest

from app import create_app

XSS_PAYLOAD = '<script>alert("xss")</script>'

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


def test_script_tag_in_project_description_is_not_executed_and_returned_as_json(client):
    payload = dict(VALID_LEAD_PAYLOAD)
    payload["project_description"] = XSS_PAYLOAD
    resp = client.post("/api/leads", json=payload)
    assert resp.status_code == 201
    # JSON responses are never HTML-interpreted by a browser, so this is
    # inherently safe as long as the content type stays application/json.
    assert resp.content_type.startswith("application/json")


def test_chat_message_with_script_tag_is_handled_safely(client):
    resp = client.post("/api/chat/message", json={"message": XSS_PAYLOAD, "session_id": "s1"})
    assert resp.status_code == 200
    assert resp.content_type.startswith("application/json")
    # The bot's own response text never echoes raw customer input verbatim
    # as markup — it's either a fixed message or FAQ content from our own
    # curated JSON files (which the schema validator already blocks script
    # tags from — see test_service_faq_schema.py).
    body = resp.get_json()
    assert "<script>" not in (body.get("response") or "")


def test_faq_schema_blocks_script_content_end_to_end():
    """Belt-and-suspenders: confirm the knowledge base actually loaded with
    no script content anywhere, since chat responses are sourced from it."""
    from pathlib import Path

    from app.services.knowledge_service import KnowledgeService

    faq_root = Path(__file__).resolve().parents[2] / "app" / "data" / "faqs"
    ks = KnowledgeService(faq_root=faq_root)
    ks.load(strict=True)
    assert not ks.load_errors
