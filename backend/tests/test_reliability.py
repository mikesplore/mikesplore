from types import SimpleNamespace

from app.main import MAX_UPLOAD_BYTES
from bot.app.llm import groq_error_message


def test_upload_limit_is_five_megabytes():
    assert MAX_UPLOAD_BYTES == 5 * 1024 * 1024


def test_groq_error_messages_are_specific():
    assert "format" in groq_error_message(SimpleNamespace(status_code=400))
    assert "too large" in groq_error_message(SimpleNamespace(status_code=413))
    assert "rate-limited" in groq_error_message(SimpleNamespace(status_code=429))
    assert "unavailable" in groq_error_message(SimpleNamespace(status_code=503))
