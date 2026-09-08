"""Groq error formatting helpers."""

import re

from groq import APIStatusError

_DURATION_TOKEN = re.compile(r"(\d+(?:\.\d+)?)([hms])")
_WINDOW_SUBSTRING = re.compile(r"in\s+(?:\d+(?:\.\d+)?[hms]\s*)+")


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


def _retry_window_text(provider: str | None) -> str | None:
    """Convert a provider retry window (_e.g._ ``16m8.544s``) to plain words.

    Returns values such as ``"16 minutes"``, ``"1 minute"``, or ``"2 hours"``;
    returns ``None`` when the provider message has no numeric retry window.
    """
    if not provider:
        return None
    match = _WINDOW_SUBSTRING.search(provider)
    if not match:
        return None
    parts = _DURATION_TOKEN.findall(match.group(0))
    if not parts:
        return None
    total_seconds = 0.0
    for value, unit in parts:
        amount = float(value)
        if unit == "h":
            total_seconds += amount * 3600
        elif unit == "m":
            total_seconds += amount * 60
        else:
            total_seconds += amount
    minutes = max(1, round(total_seconds / 60))
    if minutes >= 120:
        return f"{round(minutes / 60)} hours"
    if minutes >= 60:
        return "over an hour"
    return f"{minutes} minute{'s' if minutes != 1 else ''}"


def groq_error_message(error: APIStatusError) -> str:
    """Build a user-facing Groq error message, keeping it short.

    Groq's 429 responses carry a body such as ``{'error': {'message':
    'Rate limit reached for model ... Limit 200000, Used 198042, Requested
    3283. Please try again in 9m32.4s.', 'type': 'tokens', 'code':
    'rate_limit_exceeded'}}``. The full detail is logged, but the user only
    needs the retry window, so the message is condensed to something like
    "Groq rate limit reached. Please try again in about 10 minutes."
    """
    status = getattr(error, "status_code", None)
    provider = _provider_message(error)
    if status == 429:
        window = _retry_window_text(provider)
        if window:
            return f"Groq rate limit reached. Please try again in about {window}."
        retry = _retry_after_seconds(error)
        if retry:
            return f"Groq rate limit reached. Please try again in about {retry} seconds."
        return "Groq rate limit reached. Please try again later."
    if status == 400:
        base = "Groq rejected the request format. Please retry with a shorter job description."
    elif status == 413:
        base = "The request was too large for Groq. The CV context or job description must be shortened."
    elif status and status >= 500:
        base = "Groq is temporarily unavailable. Please try again shortly."
    else:
        base = f"Groq returned an unexpected API error{f' ({status})' if status else ''}."
    return base


def friendly_error(error: Exception, fallback: str) -> str:
    """Return a Groq-originated message, otherwise the caller's fallback.

    Handlers use this instead of swallowing ``except Exception`` blocks, so a
    rate-limit message such as "Groq rate limit reached. Please try again in
    about 10 minutes." reaches the user while unrelated errors keep the
    existing generic wording.
    """
    message = str(error)
    if message.startswith(("Groq ", "The request was too large for Groq")):
        return message[:800]
    return fallback
