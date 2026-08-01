import pytest

from app.services import smtp_transport


def test_not_configured_when_smtp_host_missing(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    assert not smtp_transport.is_configured()


def test_configured_when_smtp_host_set(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    assert smtp_transport.is_configured()


def test_send_is_noop_when_not_configured(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    result = smtp_transport.send(to="a@example.com", subject="Test", body="Hello")
    assert result is False


def test_send_returns_false_and_does_not_raise_on_connection_failure(monkeypatch):
    # 127.0.0.1 with nothing listening refuses instantly — avoids any slow
    # DNS lookup in a sandboxed/restricted network environment.
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SMTP_PORT", "1")
    monkeypatch.setenv("EMAIL_FROM_ADDRESS", "noreply@example.com")
    result = smtp_transport.send(to="a@example.com", subject="Test", body="Hello")
    assert result is False


def test_send_returns_false_when_no_from_address_available(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.delenv("EMAIL_FROM_ADDRESS", raising=False)
    monkeypatch.delenv("SMTP_USERNAME", raising=False)
    result = smtp_transport.send(to="a@example.com", subject="Test", body="Hello")
    assert result is False
