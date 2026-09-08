"""Groq error formatting helpers."""

from groq import APIStatusError


def _provider_message(error: APIStatusError) -> str | None:
    """Return the provider's error detail message when the response body has one."""
    body = getattr(error, "body", None)
    if not isinstance(body, dict):
        return None
    detail = body.get("error")
    if not isinstance(detail, dict):
        return None
    message = detail.get("message")
    if isinstance(message, str) and message.strip():
        return message.strip()
    return None


def _retry_after_seconds(error: APIStatusError) -> int | None:
    """Return the Retry-After response header as whole seconds, when present."""
    response = getattr(error, "response", None)
    if response is None:
        return None
    try:
        header = response.headers.get("retry-after")
    except Exception:
        return None
    if header is None:
        return None
    try:
        return max(1, int(float(str(header))))
    except (TypeError, ValueError):
        return None


def groq_error_message(error: APIStatusError) -> str:
    """Build a user-facing Groq error message, preferring the provider's detail.

    Groq's 429 responses carry a body such as ``{'error': {'message':
    'Rate limit reached for model ... Limit 200000, Used 198042, Requested
    3283. Please try again in 9m32.4s.', 'type': 'tokens', 'code':
    'rate_limit_exceeded'}}``. That message contains the actionable retry
    window and quota numbers, so it is surfaced verbatim instead of a generic
    fallback whenever it is available.
    """
    status = getattr(error, "status_code", None)
    provider = _provider_message(error)
    if status == 429:
        if provider:
            return f"Groq rate limit reached. {provider}"
        retry = _retry_after_seconds(error)
        if retry:
            return f"Groq rate-limited this request. Please try again in about {retry} seconds."
        return "Groq rate-limited this request. Please wait a moment and try again."
    if status == 400:
        base = "Groq rejected the request format. Please retry with a shorter job description."
    elif status == 413:
        base = "The request was too large for Groq. The CV context or job description must be shortened."
    elif status and status >= 500:
        base = "Groq is temporarily unavailable. Please try again shortly."
    else:
        base = f"Groq returned an unexpected API error{f' ({status})' if status else ''}."
    return f"{base} {provider}" if provider else base


def friendly_error(error: Exception, fallback: str) -> str:
    """Return a Groq-originated detail message, otherwise the caller's fallback.

    Handlers use this instead of swallowing ``except Exception`` blocks, so a
    rate-limit detail such as "Please try again in 9m32.4s" reaches the user
    while unrelated errors keep the existing generic wording.
    """
    message = str(error)
    if message.startswith(("Groq ", "The request was too large for Groq")):
        return message[:800]
    return fallback
