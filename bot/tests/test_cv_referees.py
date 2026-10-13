import asyncio

from bot.app import cv_handlers


class FakeMessage:
    def __init__(self, text):
        self.text = text
        self.replies = []
        self.from_user = type("User", (), {"id": 7})()

    async def answer(self, text, **kwargs):
        self.replies.append((text, kwargs))


def run_manage(monkeypatch, text, referees):
    validated = []
    base = {"data": {"name": "Owner", "referees": referees}, "revision": "rev-1"}

    async def get_base():
        return base

    async def validate(data):
        validated.append(data)
        return data

    monkeypatch.setattr(cv_handlers, "get_cv_base", get_base, raising=False)
    monkeypatch.setattr(cv_handlers, "validate_cv_base", validate, raising=False)
    monkeypatch.setattr(cv_handlers, "pending_cv_referee", {}, raising=False)
    monkeypatch.setattr(cv_handlers, "InlineKeyboardButton", lambda **kwargs: kwargs, raising=False)
    monkeypatch.setattr(cv_handlers, "InlineKeyboardMarkup", lambda **kwargs: kwargs, raising=False)
    monkeypatch.setattr(cv_handlers, "friendly_error", lambda _error, fallback: fallback, raising=False)
    monkeypatch.setattr(cv_handlers, "logger", __import__("logging").getLogger(__name__), raising=False)
    message = FakeMessage(text)
    asyncio.run(cv_handlers.manage_referees(message))
    return message, validated


def test_add_reference_prepares_reviewable_proposal(monkeypatch):
    message, validated = run_manage(
        monkeypatch,
        "/referees add Jane Doe | Engineering Manager | Example Co. | jane@example.com |",
        [],
    )
    assert validated[0]["referees"] == [{
        "name": "Jane Doe", "title": "Engineering Manager", "organization": "Example Co.",
        "email": "jane@example.com",
    }]
    proposal = cv_handlers.pending_cv_referee[7]
    assert proposal["data"]["referees"] == validated[0]["referees"]
    assert proposal["base_revision"] == "rev-1"
    assert "Add referee Jane Doe" in message.replies[0][0]
    assert "cv-referee:save:" in message.replies[0][1]["reply_markup"]["inline_keyboard"][0][0]["callback_data"]


def test_remove_reference_prepares_reviewable_proposal(monkeypatch):
    message, validated = run_manage(
        monkeypatch,
        "/referees remove 1",
        [{"name": "Jane Doe", "email": "jane@example.com"}],
    )
    assert validated[0]["referees"] == []
    assert cv_handlers.pending_cv_referee[7]["data"]["referees"] == []
    assert "Remove referee Jane Doe" in message.replies[0][0]
