import pytest

from app import create_app


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def test_404_returns_consistent_json_shape(client):
    resp = client.get("/this-route-does-not-exist")
    assert resp.status_code == 404
    body = resp.get_json()
    assert body["error"] == "not_found"
    assert "message" in body


def test_405_returns_consistent_json_shape(client):
    # /health only supports GET
    resp = client.post("/health")
    assert resp.status_code == 405
    body = resp.get_json()
    assert body["error"] == "method_not_allowed"


def test_404_response_is_json_not_html(client):
    resp = client.get("/nonexistent")
    assert resp.content_type.startswith("application/json")
