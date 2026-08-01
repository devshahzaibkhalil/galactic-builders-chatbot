import json
import logging

from app.logging_config import JsonFormatter, RedactionFilter


def _make_record(msg: str, args: tuple = ()) -> logging.LogRecord:
    return logging.LogRecord(
        name="test.logger", level=logging.INFO, pathname=__file__, lineno=1,
        msg=msg, args=args, exc_info=None,
    )


def test_redaction_filter_scrubs_email_in_message():
    record = _make_record("Lead created for jordan@example.com")
    RedactionFilter().filter(record)
    assert "jordan@example.com" not in record.msg
    assert "[REDACTED]" in record.msg


def test_redaction_filter_scrubs_email_in_args():
    record = _make_record("Lead created for %s", args=("jordan@example.com",))
    RedactionFilter().filter(record)
    assert record.args[0] == "[REDACTED]"


def test_redaction_filter_leaves_non_sensitive_message_untouched():
    record = _make_record("Lead created successfully")
    original = record.msg
    RedactionFilter().filter(record)
    assert record.msg == original


def test_json_formatter_produces_valid_json_with_expected_fields():
    record = _make_record("Something happened")
    formatted = JsonFormatter().format(record)
    parsed = json.loads(formatted)
    assert parsed["message"] == "Something happened"
    assert parsed["level"] == "INFO"
    assert "timestamp" in parsed


def test_json_formatter_and_redaction_filter_compose():
    record = _make_record("Contact email jordan@example.com about lead")
    RedactionFilter().filter(record)
    formatted = JsonFormatter().format(record)
    assert "jordan@example.com" not in formatted
    parsed = json.loads(formatted)
    assert "[REDACTED]" in parsed["message"]
