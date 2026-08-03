import base64
import json

import pytest

from app.services import smtp_transport

MAIL_ENV = (
    "EMAIL_PROVIDER", "MAILJET_API_KEY", "MAILJET_SECRET_KEY",
    "SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD",
    "EMAIL_FROM_ADDRESS", "EMAIL_FROM_NAME",
)


@pytest.fixture(autouse=True)
def clear_mail_env(monkeypatch):
    """Every test starts from a clean slate so the developer's own shell
    settings can't make these pass or fail spuriously."""
    for name in MAIL_ENV:
        monkeypatch.delenv(name, raising=False)


class _FakeResponse:
    def __init__(self, body):
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _capture_mailjet(monkeypatch, response_body='{"Messages":[{"Status":"success"}]}'):
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.data)
        return _FakeResponse(response_body)

    monkeypatch.setattr(smtp_transport.urllib.request, "urlopen", fake_urlopen)
    return captured


# --- provider selection ----------------------------------------------------

def test_defaults_to_mailjet_when_nothing_is_set():
    assert smtp_transport.active_provider() == "mailjet"


def test_infers_smtp_when_only_smtp_host_is_set(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    assert smtp_transport.active_provider() == "smtp"


def test_email_provider_overrides_inference(monkeypatch):
    monkeypatch.setenv("MAILJET_API_KEY", "key")
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    assert smtp_transport.active_provider() == "smtp"


# --- is_configured ---------------------------------------------------------

def test_not_configured_when_nothing_is_set():
    assert not smtp_transport.is_configured()


def test_not_configured_when_mailjet_secret_is_missing(monkeypatch):
    monkeypatch.setenv("MAILJET_API_KEY", "key")
    assert not smtp_transport.is_configured()


def test_configured_when_both_mailjet_credentials_present(monkeypatch):
    monkeypatch.setenv("MAILJET_API_KEY", "key")
    monkeypatch.setenv("MAILJET_SECRET_KEY", "secret")
    assert smtp_transport.is_configured()


def test_configured_when_smtp_host_set(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    assert smtp_transport.is_configured()


# --- send ------------------------------------------------------------------

def test_send_is_noop_when_not_configured():
    assert smtp_transport.send(to="a@example.com", subject="Test", body="Hello") is False


def test_send_returns_false_when_no_from_address_available(monkeypatch):
    monkeypatch.setenv("MAILJET_API_KEY", "key")
    monkeypatch.setenv("MAILJET_SECRET_KEY", "secret")
    assert smtp_transport.send(to="a@example.com", subject="Test", body="Hello") is False


def test_mailjet_send_builds_the_expected_request(monkeypatch):
    monkeypatch.setenv("MAILJET_API_KEY", "apikey")
    monkeypatch.setenv("MAILJET_SECRET_KEY", "secretkey")
    monkeypatch.setenv("EMAIL_FROM_ADDRESS", "noreply@example.com")
    monkeypatch.setenv("EMAIL_FROM_NAME", "Galactic Builders")
    captured = _capture_mailjet(monkeypatch)

    assert smtp_transport.send(to="a@example.com", subject="Test", body="Hello") is True

    assert captured["url"] == smtp_transport.MAILJET_API_URL
    scheme, _, encoded = captured["headers"]["Authorization"].partition(" ")
    assert scheme == "Basic"
    assert base64.b64decode(encoded).decode() == "apikey:secretkey"
    message = captured["payload"]["Messages"][0]
    assert message["From"] == {"Email": "noreply@example.com", "Name": "Galactic Builders"}
    assert message["To"] == [{"Email": "a@example.com"}]
    assert message["Subject"] == "Test"
    assert message["TextPart"] == "Hello"


def test_quotes_are_stripped_from_env_values(monkeypatch):
    """Render stores values literally, so a pasted .env keeps its quotes."""
    monkeypatch.setenv("MAILJET_API_KEY", '"apikey"')
    monkeypatch.setenv("MAILJET_SECRET_KEY", '"secretkey"')
    monkeypatch.setenv("EMAIL_FROM_ADDRESS", '"noreply@example.com"')
    monkeypatch.setenv("EMAIL_FROM_NAME", '"Galactic Builders"')
    captured = _capture_mailjet(monkeypatch)

    assert smtp_transport.send(to="a@example.com", subject="Test", body="Hello") is True

    message = captured["payload"]["Messages"][0]
    assert message["From"] == {"Email": "noreply@example.com", "Name": "Galactic Builders"}
    encoded = captured["headers"]["Authorization"].split()[1]
    assert base64.b64decode(encoded).decode() == "apikey:secretkey"


def test_mailjet_refusal_with_http_200_is_reported_as_failure(monkeypatch):
    """Mailjet answers 200 with Status=error when the sender isn't validated;
    that must not be recorded as a successful delivery."""
    monkeypatch.setenv("MAILJET_API_KEY", "apikey")
    monkeypatch.setenv("MAILJET_SECRET_KEY", "secretkey")
    monkeypatch.setenv("EMAIL_FROM_ADDRESS", "noreply@example.com")
    _capture_mailjet(
        monkeypatch,
        response_body=json.dumps(
            {"Messages": [{"Status": "error",
                           "Errors": [{"ErrorMessage": "sender not validated"}]}]}
        ),
    )

    assert smtp_transport.send(to="a@example.com", subject="Test", body="Hello") is False


def test_mailjet_send_does_not_raise_on_transport_failure(monkeypatch):
    monkeypatch.setenv("MAILJET_API_KEY", "apikey")
    monkeypatch.setenv("MAILJET_SECRET_KEY", "secretkey")
    monkeypatch.setenv("EMAIL_FROM_ADDRESS", "noreply@example.com")

    def boom(request, timeout=None):
        raise OSError("network down")

    monkeypatch.setattr(smtp_transport.urllib.request, "urlopen", boom)
    assert smtp_transport.send(to="a@example.com", subject="Test", body="Hello") is False


def test_smtp_send_returns_false_and_does_not_raise_on_connection_failure(monkeypatch):
    # 127.0.0.1 with nothing listening refuses instantly — avoids any slow
    # DNS lookup in a sandboxed/restricted network environment.
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SMTP_PORT", "1")
    monkeypatch.setenv("EMAIL_FROM_ADDRESS", "noreply@example.com")
    assert smtp_transport.send(to="a@example.com", subject="Test", body="Hello") is False


def test_smtp_send_returns_false_when_no_from_address_available(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    assert smtp_transport.send(to="a@example.com", subject="Test", body="Hello") is False
