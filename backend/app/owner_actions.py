"""Allowlisted owner operations exposed to the voice UI."""

OWNER_ACTIONS = {
    "replace_cv": {"label": "Replace CV", "kind": "file", "accept": ["application/pdf"]},
    "update_profile": {"label": "Update profile", "kind": "form", "fields": ["name", "tagline", "location", "focus", "experience", "availability_status", "availability_detail", "about"]},
    "edit_project": {"label": "Edit project", "kind": "entry", "content_type": "project"},
    "edit_certificate": {"label": "Edit certificate", "kind": "certificate"},
    "edit_link": {"label": "Edit contact link", "kind": "profile_link"},
    "edit_skill": {"label": "Edit skills", "kind": "skill_group"},
    "edit_education": {"label": "Edit education", "kind": "education"},
    "edit_bucket_list": {"label": "Edit bucket list", "kind": "bucket_list"},
}


def owner_action_catalog() -> list[dict]:
    return [{"action": action, **definition} for action, definition in OWNER_ACTIONS.items()]
