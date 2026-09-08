"""Shared Groq client and deterministic request defaults."""

import json
import time

import httpx

from groq import APIStatusError, AsyncGroq

from ..config import settings
from .errors import groq_error_message

client = AsyncGroq(api_key=settings.groq_api_key)
client_answer_kwargs = {"temperature": 0}


async def _record_usage(payload: dict) -> None:
    try:
        async with httpx.AsyncClient(base_url=settings.backend_url, timeout=5) as http:
            response = await http.post("/internal/llm-usage", json=payload, headers={"X-Service-Api-Key": settings.service_api_key})
            response.raise_for_status()
    except Exception:
        # Observability must never make the assistant request fail.
        return


async def complete(**kwargs):
    """Run a chat completion, converting Groq API errors into user-facing messages.

    Groq's ``RateLimitError`` (429) carries provider details such as the model,
    quota and an exact retry window in ``error.body``. Converting here, at the
    single choke point, guarantees every LLM call site surfaces that detail
    instead of letting a raw SDK error bubble up to a generic handler.
    """
    workflow = kwargs.pop("_usage_workflow", "unknown")
    started = time.perf_counter()
    try:
        completion = await client.chat.completions.create(**kwargs)
        usage = completion.usage
        prompt_details = getattr(usage, "prompt_tokens_details", None)
        await _record_usage({
            "provider": "groq", "model": kwargs.get("model", "unknown"), "workflow": workflow,
            "request_id": getattr(completion, "id", None),
            "input_tokens": getattr(usage, "prompt_tokens", None),
            "cached_input_tokens": getattr(prompt_details, "cached_tokens", None) if prompt_details else None,
            "output_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
            "input_characters": len(json.dumps(kwargs.get("messages", []), ensure_ascii=False)),
            "tool_payload_characters": len(json.dumps(kwargs.get("tools", []), ensure_ascii=False)),
            "latency_ms": round((time.perf_counter() - started) * 1000), "success": True,
        })
        return completion
    except APIStatusError as error:
        await _record_usage({"provider": "groq", "model": kwargs.get("model", "unknown"), "workflow": workflow, "latency_ms": round((time.perf_counter() - started) * 1000), "success": False, "error_code": getattr(error, "code", None) or error.__class__.__name__})
        raise ValueError(groq_error_message(error)) from error
