import pytest
from pydantic import ValidationError

from app.schemas import BulkLinkMutation, EntryCreate, EntryUpdate, ProfileLinkCreate, ProfileLinkUpdate, ProfileUpdate


def test_profile_update_rejects_contact_fields():
    with pytest.raises(ValidationError):
        ProfileUpdate.model_validate({"telegram": "mikesplore"})


def test_profile_link_requires_allowed_category():
    with pytest.raises(ValidationError):
        ProfileLinkCreate.model_validate({"name": "Telegram", "url": "https://t.me/mikesplore", "category": "personal"})


def test_profile_link_update_allows_partial_changes():
    update = ProfileLinkUpdate.model_validate({"category": "professional"})
    assert update.category == "professional"
    assert update.model_dump(exclude_unset=True) == {"category": "professional"}


def test_bulk_link_mutation_has_bounded_batch():
    request = BulkLinkMutation.model_validate({"operations": [{"action": "create", "payload": {"name": "GitHub"}}]})
    assert len(request.operations) == 1
    with pytest.raises(ValidationError):
        BulkLinkMutation.model_validate({"operations": []})


def test_entry_date_fills_year_but_explicit_year_remains_an_override():
    base = {"slug": "dated", "content_type": "project", "title": "Dated", "blurb": "Description", "date": "2022-11-09"}
    assert EntryCreate.model_validate(base).year == 2022
    assert EntryCreate.model_validate(base | {"year": 2020}).year == 2020
    assert EntryUpdate.model_validate({"date": "2023-02-01"}).year == 2023
from app.routers.admin_content import _unique_entry_slug


def test_unique_entry_slug_uses_incrementing_suffix_for_duplicates():
    class FakeSession:
        def __init__(self):
            self.calls = 0

        def scalar(self, query):
            self.calls += 1
            return "existing" if self.calls < 3 else None

    assert _unique_entry_slug("My New Project", FakeSession()) == "my-new-project-3"


def test_unique_entry_slug_replaces_unusable_titles():
    class FakeSession:
        def scalar(self, query):
            return None

    assert _unique_entry_slug("!!!", FakeSession()) == "entry"
