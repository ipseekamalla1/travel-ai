from app.core.logging import REDACTED, redact_sensitive


def test_sensitive_keys_are_redacted() -> None:
    event = redact_sensitive(
        None, "info", {"event": "login", "password": "hunter2", "Authorization": "Bearer x"}
    )

    assert event["password"] == REDACTED
    assert event["Authorization"] == REDACTED
    assert event["event"] == "login"


def test_nested_sensitive_keys_are_redacted() -> None:
    event = redact_sensitive(
        None, "info", {"headers": {"cookie": "atu_session=abc", "accept": "*/*"}}
    )

    assert event["headers"] == {"cookie": REDACTED, "accept": "*/*"}


def test_emails_in_free_text_are_masked() -> None:
    event = redact_sensitive(None, "info", {"event": "failed for maya@example.com"})

    assert event["event"] == "failed for [EMAIL]"
