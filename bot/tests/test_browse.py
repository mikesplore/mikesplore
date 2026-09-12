import asyncio

from bot.app import browse
from bot.app.callbacks import is_protected_action


def test_menu_keyboard_uses_public_callback_data_under_limit():
    keyboard = browse.menu_keyboard()
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert len(callbacks) == len(browse.MENU_ORDER)
    for callback_data in callbacks:
        assert callback_data.startswith("pub:")
        assert not is_protected_action(callback_data)
        assert len(callback_data.encode("utf-8")) <= 64


def test_entry_list_callback_data_stays_within_telegram_limit():
    for resource in browse.RESOURCE_LABELS:
        for page in (1, 999):
            data = f"pub:detail:{resource}:{page}:4"
            assert len(data.encode("utf-8")) <= 64
            assert not is_protected_action(data)


def test_parse_list_callback_defaults_to_first_page():
    assert browse.parse_list_callback("pub:list:projects") == ("projects", 1)
    assert browse.parse_list_callback("pub:list:events:3") == ("events", 3)
    assert browse.parse_list_callback("pub:list:skills:not-a-number") == ("skills", 1)


def test_parse_detail_callback_reads_coordinates():
    assert browse.parse_detail_callback("pub:detail:articles:2:4") == ("articles", 2, 4)
    assert browse.parse_detail_callback("pub:detail:projects") == ("projects", 1, 0)


def test_clip_escapes_and_truncates():
    assert browse.clip("a < b & c", 100) == "a &lt; b &amp; c"
    clipped = browse.clip("x" * 200, 50)
    assert clipped.endswith("…")
    assert len(clipped) <= 50
    assert browse.clip(None, 10) == ""


def test_format_entry_list_renders_titles_pages_and_dates():
    entries = [
        {"title": "Alpha", "blurb": "First project", "date": "2024-01-02T00:00:00Z", "tags": ["t"]},
        {"title": "Beta", "blurb": None, "year": 2023},
    ]
    text = browse.format_entry_list("Projects", entries, 1, 7)
    assert "Projects" in text and "Alpha" in text and "Beta" in text
    assert "2024-01-02" in text and "2023" in text
    assert "page 1/2" in text and "7 total" in text


def test_format_entry_list_empty_state():
    assert "No events published yet." in browse.format_entry_list("Events", [], 1, 0)


def test_entry_list_keyboard_navigation_bounds():
    entries = [{"title": f"Item {index}"} for index in range(5)]
    first = browse.entry_list_keyboard("projects", entries, 1, 12)
    last = browse.entry_list_keyboard("projects", entries, 3, 12)
    first_callbacks = [button.callback_data for row in first.inline_keyboard for button in row if button.callback_data]
    last_callbacks = [button.callback_data for row in last.inline_keyboard for button in row if button.callback_data]
    assert "pub:list:projects:2" in first_callbacks
    assert all(callback_data != "pub:list:projects:0" for callback_data in first_callbacks)
    assert "pub:list:projects:2" in last_callbacks
    assert all(callback_data != "pub:list:projects:4" for callback_data in last_callbacks)
    assert "pub:detail:projects:3:4" in last_callbacks


def test_format_entry_detail_includes_blurb_and_tags():
    entry = {"title": "Gamma", "blurb": "A short blurb", "date": "2025-02-01T00:00:00Z", "tags": ["python", "fastapi"]}
    text = browse.format_entry_detail("Articles", entry)
    assert "Gamma" in text and "A short blurb" in text
    assert "Articles · 2025-02-01" in text
    assert "python, fastapi" in text


def test_format_project_detail_uses_project_fields_and_falls_back():
    entry = {"title": "Repo title", "blurb": "Entry blurb", "date": "2024-05-01T00:00:00Z", "tags": ["tag"]}
    project = {"title": "Curated title", "status": "Live", "technologies": ["FastAPI", "Postgres"], "repositories": [{"name": "backend", "url": "https://github.com/x/y"}]}
    text = browse.format_project_detail(entry, project)
    assert "Curated title" in text and "Live" in text
    assert "FastAPI, Postgres" in text
    keyboard = browse.project_detail_keyboard(entry, project, 1)
    urls = [button.url for row in keyboard.inline_keyboard for button in row if button.url]
    assert "https://github.com/x/y" in urls
    fallback_text = browse.format_project_detail(entry, None)
    assert "Repo title" in fallback_text


def test_entry_detail_keyboard_rejects_unsafe_urls():
    keyboard = browse.entry_detail_keyboard("articles", 2, {"title": "T", "url": "javascript:alert(1)"})
    assert all(not button.url for row in keyboard.inline_keyboard for button in row)
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row if button.callback_data]
    assert "pub:list:articles:2" in callbacks


def test_single_resource_renderers():
    assert "Algorithms" in browse.format_skills([{"category": "Algorithms", "skills": ["DP", "Graphs"]}])
    contact_text = browse.format_contact([{"name": "GitHub", "url": "https://github.com/x", "handle": "@x"}])
    assert "GitHub" in contact_text and "@x" in contact_text
    cert_text = browse.format_certificates([{"title": "AWS CCP", "image_url": "https://r2/img.png"}])
    assert "AWS CCP" in cert_text
    bucket_text = browse.format_bucket_list([{"title": "Ship it", "done": True, "remark": "done"}, {"title": "Rest", "done": False}])
    assert "1/2 done" in bucket_text and "✅" in bucket_text and "⬜" in bucket_text
    about_text = browse.format_about({"name": "Mike", "tagline": "Backend engineer", "availability_status": "Open to work"})
    assert "Mike" in about_text and "Backend engineer" in about_text and "Open to work" in about_text


def test_empty_single_resource_states():
    assert "No certificates published yet." in browse.format_certificates([])
    assert "No contact links published yet." in browse.format_contact([])
    assert "Nothing published yet." in browse.format_bucket_list([])
    assert "No profile published yet." in browse.format_about({})
    assert "No skills published yet." in browse.format_skills([])


def test_menu_text_includes_counts_and_owner():
    counts = {"projects": 12, "hackathons": 7, "events": 17, "certificates": 5, "bucket_list": 23}
    text = browse.format_menu_text("Ada", "Mike", counts, 11)
    assert "Hi Ada!" in text and "Mike" in text
    assert "Projects: 12" in text and "Articles: 11" in text and "Certificates: 5" in text
    assert "Skills:" not in text


class _FakeMessage:
    def __init__(self):
        self.calls = []

    async def answer(self, text=None, **kwargs):
        self.calls.append("answer")


class _FakeCallback:
    def __init__(self, data):
        self.data = data
        self.message = _FakeMessage()
        self.answered = False

    async def answer(self, text=None, **kwargs):
        self.answered = True


def test_detail_opens_new_message_while_list_edits_in_place(monkeypatch):
    browse._cache.clear()

    async def fake_list_entries(content_type, page=1):
        return {"entries": [{"title": "One", "slug": "one", "date": "2024-01-01"}], "total": 1}

    async def fake_project_detail(slug):
        return None

    monkeypatch.setattr(browse, "list_entries", fake_list_entries)
    monkeypatch.setattr(browse, "fetch_project_detail", fake_project_detail)

    list_callback = _FakeCallback("pub:list:projects:1")
    asyncio.run(browse.handle_public_callback(list_callback))
    assert list_callback.message.calls == ["answer"]
    assert list_callback.answered

    detail_callback = _FakeCallback("pub:detail:projects:1:0")
    asyncio.run(browse.handle_public_callback(detail_callback))
    assert detail_callback.message.calls == ["answer"]
    assert detail_callback.answered

