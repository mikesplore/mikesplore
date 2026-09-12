"""Tests for the deterministic /manage content-management wizard."""

import asyncio

from bot.app import wizard
from bot.app.callbacks import is_protected_action


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class FakeMessage:
    def __init__(self, user_id=1):
        self.from_user = type("User", (), {"id": user_id})()
        self.text = ""
        self.answered = []
        self.edited = []

    async def answer(self, text, reply_markup=None):
        self.answered.append((text, reply_markup))

    async def edit_text(self, text, reply_markup=None):
        self.edited.append((text, reply_markup))


class FakeCallback:
    def __init__(self, data, user_id=1):
        self.data = data
        self.from_user = type("User", (), {"id": user_id})()
        self.message = FakeMessage(user_id)
        self.answers = []

    async def answer(self, text=None, show_alert=False):
        self.answers.append((text, show_alert))


def _configure(fakes=None):
    fakes = fakes or {}
    state = {
        "wizard_sessions": fakes.get("wizard_sessions", {}),
        "pending_upload": fakes.get("pending_upload", {}),
        "pending_upload_target": fakes.get("pending_upload_target", {}),
        "update_profile": fakes.get("update_profile"),
        "manage_content": fakes.get("manage_content"),
        "bulk_manage_links": fakes.get("bulk_manage_links"),
        "list_admin_resource": fakes.get("list_admin_resource"),
        "get_profile": fakes.get("get_profile"),
        "is_admin": lambda message: True,
    }
    wizard.configure(state)
    return state


def _session(**overrides):
    session = {
        "resource": "profile",
        "mode": "update",
        "record": None,
        "records": [],
        "records_page": 0,
        "current": {"name": "Old Name"},
        "pending": {},
        "media_done": [],
        "sub": None,
        "step": "field",
        "pending_field": None,
    }
    session.update(overrides)
    return session


# ---------------------------------------------------------------------------
# Callback scheme
# ---------------------------------------------------------------------------


def test_all_wizard_callbacks_are_protected_and_under_64_bytes():
    callbacks = []
    for resource_key in wizard.RESOURCE_ORDER:
        callbacks.append(f"mng:res:{resource_key}")
        spec = wizard.RESOURCES[resource_key]
        for field in spec["fields"]:
            callbacks.append(f"mng:field:{field['key']}")
            if field["type"] == "bool":
                callbacks.append(f"mng:bval:{field['key']}:1")
                callbacks.append(f"mng:bval:{field['key']}:0")
            if field["type"] == "select":
                for option in field.get("options", []):
                    callbacks.append(f"mng:sel:{field['key']}:{option}")
        for sub in spec.get("subs", []):
            callbacks.append(f"mng:sub:{sub}")
    callbacks += [
        "mng:yes", "mng:done", "mng:cancel", "mng:create",
        "mng:prev", "mng:next", "mng:delete", "mng:confirm-delete",
        "mng:sub-add", "mng:sub-done",
    ]
    assert callbacks
    for data in callbacks:
        assert is_protected_action(data), f"not protected: {data}"
        assert len(data.encode("utf-8")) <= 64, f"too long: {data}"


def test_parse_callback_reads_action_and_args():
    assert wizard.parse_callback("mng:res:profile") == ("res", ["profile"])
    assert wizard.parse_callback("mng:bval:is_visible:1") == ("bval", ["is_visible", "1"])
    assert wizard.parse_callback("mng:done") == ("done", [])
    assert wizard.parse_callback("pub:list:projects") == ("unknown", [])


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_validate_value_text_and_textarea():
    assert wizard.validate_value({"type": "text"}, "  Mike  ") == ("Mike", None)
    value, error = wizard.validate_value({"type": "text"}, "   ")
    assert value is None and error


def test_validate_value_url_and_slug():
    assert wizard.validate_value({"type": "url"}, "https://github.com/a") == ("https://github.com/a", None)
    _, error = wizard.validate_value({"type": "url"}, "github.com/a")
    assert error
    assert wizard.validate_value({"type": "slug"}, "My Cool App") == ("my-cool-app", None)
    _, error = wizard.validate_value({"type": "slug"}, "My_Cool_App")
    assert error


def test_validate_value_date_year_int():
    assert wizard.validate_value({"type": "date"}, "2024-06-01") == ("2024-06-01", None)
    _, error = wizard.validate_value({"type": "date"}, "01-06-2024")
    assert error
    assert wizard.validate_value({"type": "year"}, "2024") == (2024, None)
    _, error = wizard.validate_value({"type": "year"}, "400")
    assert error
    assert wizard.validate_value({"type": "int"}, "-3") == (-3, None)
    _, error = wizard.validate_value({"type": "int"}, "3.5")
    assert error


def test_validate_value_tags_dedupes():
    assert wizard.validate_value({"type": "tags"}, "python, docker, python") == (["python", "docker"], None)
    value, error = wizard.validate_value({"type": "tags"}, " , ")
    assert error or not value


def test_validate_value_bool_and_select():
    assert wizard.validate_value({"type": "bool"}, "yes") == (True, None)
    assert wizard.validate_value({"type": "bool"}, "off") == (False, None)
    field = {"type": "select", "options": ["professional", "social", "contact"]}
    assert wizard.validate_value(field, "social") == ("social", None)
    _, error = wizard.validate_value(field, "work")
# ---------------------------------------------------------------------------
# Pagination, create queue, finish ops
# ---------------------------------------------------------------------------


def test_page_records_clamps_bounds():
    records = [{"id": i} for i in range(12)]
    page, index, pages = wizard.page_records(records, 2)
    assert index == 2 and pages == 3
    assert [item["id"] for item in page] == [10, 11]
    _, index, pages = wizard.page_records(records, 99)
    assert index == 2 and pages == 3
    _, index, pages = wizard.page_records([], 0)
    assert index == 0 and pages == 1


def test_advance_create_queue_moves_through_required_fields():
    session = _session(resource="projects", step="create", create_queue=["slug", "title", "blurb"], pending_field="slug")
    wizard.advance_create_queue(session)
    assert session["pending_field"] == "title" and session["step"] == "create"
    wizard.advance_create_queue(session)
    assert session["pending_field"] == "blurb" and session["step"] == "create"
    wizard.advance_create_queue(session)
    assert session["step"] == "field" and "create_queue" not in session


def test_build_finish_ops_profile_only_changed_keys():
    session = _session(resource="profile", pending={"name": "Mike", "tagline": "New tagline"})
    ops = wizard.build_finish_ops(session)
    assert ops == [
        {"resource": "profile", "action": "update", "id": None, "payload": {"name": "Mike", "tagline": "New tagline"}}
    ]


def test_build_finish_ops_entries_update_includes_id_and_only_pending():
    session = _session(resource="projects", record={"id": "abc", "label": "P"}, pending={"title": "New Title"})
    ops = wizard.build_finish_ops(session)
    assert ops == [
        {"resource": "entries", "action": "update", "id": "abc", "payload": {"title": "New Title", "id": "abc"}}
    ]


def test_build_finish_ops_entries_create_sets_content_type():
    session = _session(resource="projects", mode="create", pending={"slug": "p", "title": "P", "blurb": "B"})
    ops = wizard.build_finish_ops(session)
    assert ops == [
        {
            "resource": "entries",
            "action": "create",
            "id": None,
            "payload": {"slug": "p", "title": "P", "blurb": "B", "content_type": "project"},
        }
    ]


def test_build_finish_ops_empty_pending_returns_no_ops():
    assert wizard.build_finish_ops(_session(resource="profile")) == []


def test_build_finish_ops_links_uses_collection_resource():
    session = _session(resource="links", record={"id": "l1", "label": "GitHub"}, pending={"url": "https://github.com/x"})
    ops = wizard.build_finish_ops(session)
    assert ops[0]["resource"] == "links" and ops[0]["payload"]["url"].startswith("https://")


# ---------------------------------------------------------------------------
# Summary rendering and pickers
# ---------------------------------------------------------------------------


def test_render_summary_formats_pending_types():
    session = _session(
        pending={"is_visible": True, "tags": ["a", "b"], "about": "Hi", "name": None},
        media_done=["Profile photo"],
    )
    text = wizard.render_summary(session)
    assert "Yes" in text and "a, b" in text and "Hi" in text
    assert "(cleared)" in text
    assert "attached (saved immediately)" in text


def test_render_summary_empty_state():
    assert "No changes yet." in wizard.render_summary(_session())


def test_field_keyboard_hides_media_in_create_mode_and_shows_subs_in_update():
    create = _session(resource="projects", mode="create", step="field")
    create_kb = wizard.field_keyboard(create)
    create_callbacks = [b.callback_data for row in create_kb.inline_keyboard for b in row]
    assert "mng:field:card_image" not in create_callbacks
    assert "mng:sub:technologies" not in create_callbacks

    update = _session(resource="projects", current={"title": "Old"}, step="field")
    update_kb = wizard.field_keyboard(update)
    update_callbacks = [b.callback_data for row in update_kb.inline_keyboard for b in row]
    assert "mng:field:card_image" in update_callbacks
    assert "mng:sub:repositories" in update_callbacks
    assert "mng:field:title" in update_callbacks


def test_record_keyboard_pages_and_adds_new():
    session = _session(resource="projects", records=[{"id": i, "title": f"P{i}"} for i in range(7)], records_page=1)
    kb = wizard.record_keyboard(session)
    callbacks = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert "mng:rec:5" in callbacks and "mng:create" in callbacks and "mng:prev" in callbacks
    assert "mng:rec:0" not in callbacks


def test_record_label_uses_title_for_entries():
    assert wizard.record_label("projects", {"title": "X", "slug": "x"}) == "X"
# ---------------------------------------------------------------------------
# Handler-level behaviour with fakes
# ---------------------------------------------------------------------------


def test_handle_wizard_text_stores_validation_and_returns_true():
    _configure()
    message = FakeMessage()
    message.text = "New Name"
    session = _session(step="value", pending_field="name", current={"name": "Old"})
    handled = asyncio.run(wizard.handle_wizard_text(message, session))
    assert handled and session["pending"]["name"] == "New Name"
    assert session["step"] == "field"
    assert message.answered and message.answered[0][0]  # summary posted


def test_handle_wizard_text_rejects_invalid_value():
    _configure()
    message = FakeMessage()
    message.text = "2024-13-99"
    session = _session(resource="projects", step="value", pending_field="date", current={})
    handled = asyncio.run(wizard.handle_wizard_text(message, session))
    assert handled and "date" not in session.get("pending", {})
    assert message.answered[0][0].startswith("❌")


def test_handle_wizard_text_ignored_outside_value_steps():
    _configure()
    message = FakeMessage()
    session = _session(step="field")
    handled = asyncio.run(wizard.handle_wizard_text(message, session))
    assert not handled


def test_handle_wizard_text_accepts_select_and_nudges_media():
    _configure()
    message = FakeMessage()
    message.text = "social"
    session = _session(resource="links", step="value", pending_field="category", current={})
    handled = asyncio.run(wizard.handle_wizard_text(message, session))
    assert handled and session["pending"]["category"] == "social"

    media_message = FakeMessage()
    media_message.text = "hello"
    media_session = _session(resource="profile", step="media", pending_field="photo")
    handled = asyncio.run(wizard.handle_wizard_text(media_message, media_session))
    assert handled
    assert "photo or document" in media_message.answered[0][0]


def test_cancel_callback_clears_session_and_edits_message():
    sessions = {1: _session()}
    _configure({"wizard_sessions": sessions})
    callback = FakeCallback("mng:cancel")
    asyncio.run(wizard.handle_wizard_callback(callback))
    assert 1 not in sessions
    assert callback.message.edited and callback.message.edited[0][0] == "Cancelled."


def test_finish_save_applies_ops_and_clears_session():
    applied = []
    applied_payloads = []

    async def fake_update(payload):
        applied_payloads.append(payload)

    async def fake_manage(resource, action, payload):
        applied.append((resource, action, payload))

    sessions = {1: _session(resource="profile", pending={"name": "Mike"})}
    _configure(
        {
            "wizard_sessions": sessions,
            "update_profile": fake_update,
            "manage_content": fake_manage,
            "bulk_manage_links": lambda ops: ops,
        }
    )
    callback = FakeCallback("mng:done")
    asyncio.run(wizard.finish_save(callback, sessions[1]))
    assert applied_payloads == [{"name": "Mike"}]
    assert 1 not in sessions
    assert callback.message.edited and callback.message.edited[0][0] == "✅ Saved."


def test_media_upload_complete_requires_active_media_step():
    sessions = {1: _session()}
    _configure({"wizard_sessions": sessions})
    message = FakeMessage()
    asyncio.run(wizard.media_upload_complete(message))
    assert not sessions[1].get("media_done")

    sessions[1]["step"] = "media"
    sessions[1]["pending_field"] = "photo"
    asyncio.run(wizard.media_upload_complete(message))
    assert "Profile photo" in sessions[1]["media_done"]
    assert sessions[1]["step"] == "field"
    assert message.answered  # summary posted


def test_prepare_media_upload_arms_pending_upload_for_entry():
    pending_upload = {}
    pending_upload_target = {}
    _configure({"pending_upload": pending_upload, "pending_upload_target": pending_upload_target})
    message = FakeMessage()
    session = _session(resource="projects", step="media", pending_field="card_image", record={"id": "e1", "label": "P"})
    asyncio.run(wizard.prepare_media_upload(message, session))
    assert pending_upload[1][0] == "project-image"
    assert pending_upload_target[1] == {"entry_id": "e1", "role": "card"}