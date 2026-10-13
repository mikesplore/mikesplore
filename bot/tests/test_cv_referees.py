import asyncio

from bot.app import cv_handlers


class FakeMessage:
    def __init__(self, text):
        self.text = text
        self.replies = []

    async def answer(self, text):
        self.replies.append(text)


def run_manage(monkeypatch, text, referees):
    saved = []
    base = {"data": {"name": "Owner", "referees": referees}, "revision": "rev-1"}

    async def get_base():
        return base

    async def validate(data):
        return data

    async def save(data, base_revision=None):
        saved.append((data, base_revision))

    monkeypatch.setattr(cv_handlers, "get_cv_base", get_base, raising=False)
    monkeypatch.setattr(cv_handlers, "validate_cv_base", validate, raising=False)
    monkeypatch.setattr(cv_handlers, "save_cv_base", save, raising=False)
    monkeypatch.setattr(cv_handlers, "friendly_error", lambda _error, fallback: fallback, raising=False)
    monkeypatch.setattr(cv_handlers, "logger", __import__("logging").getLogger(__name__), raising=False)
    message = FakeMessage(text)
    asyncio.run(cv_handlers.manage_referees(message))
    return message, saved


def test_add_reference_saves_with_revision_check(monkeypatch):
    message, saved = run_manage(
        monkeypatch,
        "/referees add Jane Doe | Engineering Manager | Example Co. | jane@example.com |",
        [],
    )
    assert saved[0][0]["referees"] == [{
        "name": "Jane Doe", "title": "Engineering Manager", "organization": "Example Co.",
        "email": "jane@example.com",
    }]
    assert saved[0][1] == "rev-1"
    assert "Added Jane Doe" in message.replies[0]


def test_remove_reference_uses_one_based_list_number(monkeypatch):
    message, saved = run_manage(
        monkeypatch,
        "/referees remove 1",
        [{"name": "Jane Doe", "email": "jane@example.com"}],
    )
    assert saved[0][0]["referees"] == []
    assert "Removed Jane Doe" in message.replies[0]
