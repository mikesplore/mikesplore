"""Groq client configuration."""

from groq import AsyncGroq
from ..config import settings

client = AsyncGroq(api_key=settings.groq_api_key)
client_answer_kwargs = {"temperature": 0}
