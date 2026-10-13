from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from fastapi import Response

from app.main import list_entries
from app.models import Entry


class FakeSession:
    def __init__(self, entries):
        self.entries = entries
        self.media_rows = []

    def scalars(self, query):
        class Result:
            def all(inner):
                return [entry for entry in self.entries if entry.is_visible]
        return Result()

    def scalar(self, query):
        return len(self.entries)

    def execute(self, query):
        class Result:
            def all(inner):
                return self.media_rows
        return Result()


def test_public_list_excludes_invisible_entries():
    now = datetime.now(timezone.utc)
    visible = Entry(id=uuid4(), slug="visible", content_type="project", title="Visible", blurb="ok", date=date.today(), is_visible=True, is_featured=False, custom_order=0, tags=[], source={}, created_at=now, updated_at=now)
    hidden = Entry(id=uuid4(), slug="hidden", content_type="project", title="Hidden", blurb="no", date=date.today(), is_visible=False, is_featured=False, custom_order=0, tags=[], source={}, created_at=now, updated_at=now)
    result = list_entries(page=1, page_size=5, db=FakeSession([visible, hidden]), response=Response())
    assert len(result) == 1
    assert result[0]["slug"] == "visible"
    assert result[0]["media"] == []


def test_public_entry_list_includes_attached_media():
    now = datetime.now(timezone.utc)
    visible = Entry(id=uuid4(), slug="visible", content_type="event", title="Visible", blurb="ok", date=date.today(), is_visible=True, is_featured=False, custom_order=0, tags=[], source={}, created_at=now, updated_at=now)
    session = FakeSession([visible])
    link = SimpleNamespace(id=4, entry_id=visible.id, role="card", alt_text="Stage", caption="Event", custom_order=2)
    asset = SimpleNamespace(id=9, url="https://cdn.example/event.jpg", label="Event cover")
    session.media_rows = [(link, asset)]
    result = list_entries(page=1, page_size=5, db=session, response=Response())
    assert result[0]["media"] == [{
        "id": 4, "asset_id": 9, "role": "card", "url": "https://cdn.example/event.jpg",
        "label": "Event cover", "alt_text": "Stage", "caption": "Event", "custom_order": 2,
    }]
