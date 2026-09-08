"""Shared Groq client and deterministic request defaults."""

from groq import APIStatusError, AsyncGroq

from ..config import settings
from .errors import groq_error_message

client = AsyncGroq(api_key=settings.groq_api_key)
client_answer_kwargs = {"temperature": 0}


async def complete(**kwargs):
    """Run a chat completion, converting Groq API errors into user-facing messages.

    Groq's ``RateLimitError`` (429) carries provider details such as the model,
    quota and an exact retry window in ``error.body``. Converting here, at the
    single choke point, guarantees every LLM call site surfaces that detail
    instead of letting a raw SDK error bubble up to a generic handler.
    """
    try:
        return await client.chat.completions.create(**kwargs)
    except APIStatusError as error:
        raise ValueError(groq_error_message(error)) from error
