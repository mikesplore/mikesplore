from bot.app import cv_projects


def test_cv_project_copy_uses_source_identity_and_evidence():
    result = cv_projects._copy_source_project({
        "id": "client-dashboard",
        "name": "Client Dashboard",
        "date": "2025",
        "stack": ["Python", "FastAPI"],
        "evidence": ["Built an owner dashboard.", "Added role-based access."],
    })

    assert result == {
        "id": "client-dashboard",
        "name": "Client Dashboard",
        "date": "2025",
        "stack": "Python, FastAPI",
        "bullets": ["Built an owner dashboard.", "Added role-based access."],
    }


def test_project_actions_are_bound_to_revision_and_desired_state(monkeypatch):
    monkeypatch.setattr(cv_projects, "InlineKeyboardButton", lambda **kwargs: kwargs, raising=False)
    monkeypatch.setattr(cv_projects, "InlineKeyboardMarkup", lambda **kwargs: kwargs, raising=False)
    context = {"revision": "0123456789abcdef" + "0" * 48}

    include = cv_projects._detail_markup(2, 1, False, context)["inline_keyboard"][0][0]
    remove = cv_projects._detail_markup(2, 1, True, context)["inline_keyboard"][0][0]

    assert include["callback_data"] == "cvp:include:0123456789abcdef:2"
    assert remove["callback_data"] == "cvp:remove:0123456789abcdef:2"
