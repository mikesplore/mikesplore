"""Shared callback-query helpers for Telegram inline actions."""

from aiogram.exceptions import TelegramBadRequest


async def acknowledge(callback, text: str | None = None, *, show_alert: bool = False, logger=None) -> bool:
    """Acknowledge a callback without allowing stale Telegram queries to fail the webhook."""
    try:
        await callback.answer(text, show_alert=show_alert)
        return True
    except TelegramBadRequest:
        if logger:
            logger.info("Telegram callback acknowledgement expired")
        return False


def is_protected_action(data: str) -> bool:
    return data.startswith(("admin:", "cv:", "upload:", "gallery:", "adminlist:", "mng:"))
