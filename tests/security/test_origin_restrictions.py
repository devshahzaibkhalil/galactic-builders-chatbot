import pytest

from app import create_app


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def test_approved_origin_receives_cors_header(client):
    resp = client.get("/health", headers={"Origin": "https://galacticbuilldersllc.com"})
    assert resp.headers.get("Access-Control-Allow-Origin") == "https://galacticbuilldersllc.com"


def test_www_subdomain_also_approved(client):
    resp = client.get("/health", headers={"Origin": "https://www.galacticbuilldersllc.com"})
    assert resp.headers.get("Access-Control-Allow-Origin") == "https://www.galacticbuilldersllc.com"


def test_unapproved_origin_receives_no_cors_header(client):
    resp = client.get("/health", headers={"Origin": "https://evil-clone-site.com"})
    assert "Access-Control-Allow-Origin" not in resp.headers


def test_no_origin_header_is_fine_and_gets_no_cors_header(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "Access-Control-Allow-Origin" not in resp.headers


def test_cors_header_is_never_wildcard(client):
    resp = client.get("/health", headers={"Origin": "https://galacticbuilldersllc.com"})
    assert resp.headers.get("Access-Control-Allow-Origin") != "*"
