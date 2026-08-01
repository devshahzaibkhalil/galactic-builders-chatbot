import pytest

from app import create_app


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def test_widget_page_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/html")
    assert b"Galactic Builders" in resp.data


def test_widget_page_also_available_at_chatbot_path(client):
    resp = client.get("/chatbot")
    assert resp.status_code == 200


def test_widget_page_references_the_real_chat_api(client):
    resp = client.get("/")
    assert b"/api/chat/message" in resp.data
    assert b"/api/leads" in resp.data
