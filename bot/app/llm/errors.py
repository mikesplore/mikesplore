"""Groq error formatting helpers."""

from groq import APIStatusError


def groq_error_message(error: APIStatusError) -> str:
    status = getattr(error, "status_code", None)
    if status == 400:
        return "Groq rejected the request format. Please retry with a shorter job description."
    if status == 413:
        return "The request was too large for Groq. The CV context or job description must be shortened."
    if status == 429:
        return "Groq rate-limited this request. Please wait a moment and try again."
    if status and status >= 500:
        return "Groq is temporarily unavailable. Please try again shortly."
    return f"Groq returned an unexpected API error{f' ({status})' if status else ''}."
