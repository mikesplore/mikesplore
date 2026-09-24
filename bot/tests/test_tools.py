from bot.app.tools import _filter_entry_type


def test_filter_entry_type_excludes_non_project_entries():
    entries = [
        {"content_type": "project", "title": "Portfolio"},
        {"content_type": "article", "title": "Article"},
        {"content_type": "event", "title": "Event"},
    ]

    assert _filter_entry_type(entries, "project") == [entries[0]]
    assert _filter_entry_type(entries, None) == entries
