import pytest
from pydantic import ValidationError

from app.schemas import BulkLinkMutation, ProfileLinkCreate, ProfileLinkUpdate, ProfileUpdate


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
