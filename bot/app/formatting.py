import html
import re


def telegram_html(text: str) -> str:
    """Convert the small Markdown subset used by the model to Telegram HTML."""
    value = html.escape(text, quote=False)
    value = re.sub(r"\[([^]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", value)
    value = re.sub(r"_([^_]+)_", r"<i>\1</i>", value)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    return value
