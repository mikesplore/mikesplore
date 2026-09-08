import asyncio
import importlib
from types import SimpleNamespace

import httpx
from groq import RateLimitError

from app.main import MAX_UPLOAD_BYTES
from bot.app.llm import friendly_error, groq_error_message
from bot.app.llm.client import complete

RATE_LIMIT_BODY = {
    "error": {
        "message": "Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_01kpqxk04eehatmqdkx2ammgec` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 198042, Requested 3283. Please try again in 9m32.4s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing",
        "type": "tokens",
        "code": "rate_limit_exceeded",
    }
}


def test_upload_limit_is_five_megabytes():
    assert MAX_UPLOAD_BYTES == 5 * 1024 * 1024


def test_groq_error_messages_are_specific():
    assert "format" in groq_error_message(SimpleNamespace(status_code=400))
    assert "too large" in groq_error_message(SimpleNamespace(status_code=413))
    assert "rate limit" in groq_error_message(SimpleNamespace(status_code=429))
    assert "unavailable" in groq_error_message(SimpleNamespace(status_code=503))


def test_groq_rate_limit_message_is_concise():
    error = SimpleNamespace(status_code=429, body=RATE_LIMIT_BODY, response=None)
    message = groq_error_message(error)
    assert message == "Groq rate limit reached. Please try again in about 10 minutes."
    assert "qwen/qwen3.8-27b" not in message
    assert "Limit 200000" not in message
    assert "settings/billing" not in message


def test_groq_rate_limit_message_uses_retry_after_header_when_body_absent():
    error = SimpleNamespace(status_code=429, body=None, response=SimpleNamespace(headers={"retry-after": "572"}))
    message = groq_error_message(error)
    assert "572 seconds" in message


def test_friendly_error_returns_groq_detail_and_fallback_otherwise():
    detail = groq_error_message(SimpleNamespace(status_code=429, body=RATE_LIMIT_BODY, response=None))
    assert friendly_error(ValueError(detail), "fallback") == detail
    assert friendly_error(ValueError("backend rejected the record"), "fallback") == "fallback"


def test_complete_wrapper_converts_rate_limit_error_to_concise_message(monkeypatch):
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(429, request=request, json=RATE_LIMIT_BODY)
    rate_limit = RateLimitError("Error code: 429", response=response, body=RATE_LIMIT_BODY)

    class Completions:
        async def create(self, **kwargs):
            raise rate_limit

    class Chat:
        completions = Completions()

    class FakeClient:
        chat = Chat()

    monkeypatch.setattr(importlib.import_module("bot.app.llm.client"), "client", FakeClient())
    try:
        asyncio.run(complete(model="qwen/qwen3.8-27b"))
    except ValueError as error:
        assert "Groq rate limit reached" in str(error)
        assert "10 minutes" in str(error)
        assert "qwen/qwen3.8-27b" not in str(error)
    else:
        raise AssertionError("complete() should have converted the 429 error to ValueError")
