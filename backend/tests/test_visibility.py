from datetime import date
from uuid import uuid4
from fastapi import Response

from app.main import list_entries
from app.models import Entry


class FakeSession:
    def __init__(self, entries):
        self.entries = entries

    def scalars(self, query):
        class Result:
            def all(inner):
                return [entry for entry in self.entries if entry.is_visible]
        return Result()

    def scalar(self, query):
        return len(self.entries)


def test_public_list_excludes_invisible_entries():
    visible = Entry(id=uuid4(), slug="visible", content_type="project", title="Visible", blurb="ok", date=date.today(), is_visible=True)
    hidden = Entry(id=uuid4(), slug="hidden", content_type="project", title="Hidden", blurb="no", date=date.today(), is_visible=False)
    result = list_entries(page=1, page_size=5, db=FakeSession([visible, hidden]), response=Response())
    assert result == [visible]
