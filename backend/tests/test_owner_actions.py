from app.owner_actions import OWNER_ACTIONS, owner_action_catalog


def test_owner_action_catalog_covers_all_curated_resources():
    assert set(OWNER_ACTIONS) == {
        "replace_cv",
        "update_profile",
        "edit_project",
        "edit_certificate",
        "edit_link",
        "edit_skill",
        "edit_education",
    }
    assert {item["action"] for item in owner_action_catalog()} == set(OWNER_ACTIONS)


def test_owner_action_catalog_marks_file_and_form_boundaries():
    catalog = {item["action"]: item for item in owner_action_catalog()}
    assert catalog["replace_cv"]["kind"] == "file"
    assert catalog["update_profile"]["kind"] == "form"
    assert catalog["edit_project"]["content_type"] == "project"
