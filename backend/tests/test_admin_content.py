from app.routers.admin_content import _ensure_entry_slug


class FakeSession:
    def __init__(self, existing_slugs=()):
        self.existing_slugs = set(existing_slugs)

    def scalar(self, query):
        # The helper issues a SQLAlchemy select; the fake only needs its
        # resulting slug value for this focused regression test.
        slug = query.whereclause.right.value
        return object() if slug in self.existing_slugs else None


def test_generic_entry_create_derives_unique_slug_from_title():
    payload = {"content_type": "project", "title": "Milo", "blurb": "A project"}

    _ensure_entry_slug(payload, FakeSession({"milo"}))

    assert payload["slug"] == "milo-2"


def test_generic_entry_create_preserves_supplied_slug():
    payload = {"slug": "custom-slug", "title": "Milo"}

    _ensure_entry_slug(payload, FakeSession({"milo"}))

    assert payload["slug"] == "custom-slug"
