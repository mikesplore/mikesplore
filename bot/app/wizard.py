"""Deterministic, zero-LLM content management wizard for the portfolio owner.

``/manage`` replaces the guess-and-extract approach with a button-driven
conversation: pick a resource, pick a field (current value shown), type the new
value (validated locally), and only an explicit "Finish & save" writes to the
backend. This is the admin-side sibling of the public browse mode — every
interaction reads verified REST data and renders locally, so there are no Groq
tokens and no hallucinated field values.

Callback-data scheme (all payloads stay under Telegram's 64-byte limit; record
ids/slugs are never embedded — records are addressed by page/index):

    mng:res:<resource>          -> pick a resource
    mng:rec:<index>             -> pick a record from the cached list
    mng:prev / mng:next         -> page the record list
    mng:create                  -> start a "new record" create flow
    mng:field:<key>             -> pick an editable field
    mng:bval:<key>:<0|1>        -> boolean/toggle value
    mng:sel:<key>:<value>       -> select value (options without spaces/colons)
    mng:yes                     -> "edit another field?"
    mng:done                    -> finish & save the pending batch
    mng:delete                  -> offer delete confirmation
    mng:confirm-delete          -> execute the deletion
    mng:sub:<kind>              -> open a sub-resource (technologies/repositories)
    mng:sub-add                 -> collect sub-resource input
    mng:sub-done                -> return to the field picker
    mng:cancel                  -> abandon the session

Media fields (profile photo, project images) keep the existing immediate-upload
semantics: the wizard sets ``pending_upload``/``pending_upload_target`` exactly
like the legacy upload flows, uploads.py saves the file, and the wizard reports
the result back into the summary. Text edits are batched until Finish & save.
"""

from datetime import datetime
import html
import logging
import re

import httpx
from aiogram import types

from .admin_operations import execute_admin_operation

logger = logging.getLogger(__name__)

PAGE_SIZE = 5
MAX_BUTTON_TEXT = 60
MAX_TEXT_VALUE = 4000
MAX_TEXTAREA_VALUE = 12000

# Injected by configure().
wizard_sessions = None
pending_upload = None
pending_upload_target = None
update_profile = None
manage_content = None
bulk_manage_links = None
list_admin_resource = None
get_profile = None
is_admin = None

VALUE_HINTS = {
    "text": "Short text.",
    "textarea": "Longer text is fine.",
    "url": "Must start with http:// or https://",
    "slug": "Lowercase letters, numbers and hyphens only.",
    "date": "Use YYYY-MM-DD, e.g. 2024-06-01.",
    "year": "A year, e.g. 2024.",
    "int": "A whole number.",
    "tags": "Comma-separated, e.g. python, fastapi, docker.",
}

SUB_LABELS = {
    "technologies": "🔧 Technologies",
    "repositories": "📦 Repositories",
}

# Resource aliases accepted by /manage so the command reads naturally.
ALIASES = {
    "project": "projects",
    "hackathon": "hackathons",
    "article": "articles",
    "event": "events",
    "link": "links",
    "contact": "links",
    "skill": "skills",
    "education": "education",
    "bucket": "bucket-list",
    "certificate": "certificates",
}


def _field(key, label, ftype, **extra):
    return {"key": key, "label": label, "type": ftype, **extra}


def configure(dependencies: dict) -> None:
    globals().update(dependencies)


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

ENTRY_FIELDS = [
    _field("title", "Title", "text"),
    _field("slug", "Slug", "slug"),
    _field("blurb", "Description", "textarea"),
    _field("status", "Status", "text", nullable=True),
    _field("category", "Category", "text", nullable=True),
    _field("date", "Date", "date", nullable=True),
    _field("year", "Year", "year", nullable=True),
    _field("custom_order", "List order", "int"),
    _field("is_visible", "Visible", "bool"),
    _field("is_featured", "Featured", "bool"),
    _field("tags", "Tags", "tags"),
    _field("icon_label", "Icon label", "text", nullable=True),
    _field("template", "Template", "text"),
]

RESOURCES: dict[str, dict] = {
    "profile": {
        "label": "Profile",
        "kind": "singleton",
        "write": "profile",
        "create": False,
        "fields": [
            _field("name", "Name", "text"),
            _field("tagline", "Tagline", "text", nullable=True),
            _field("location", "Location", "text", nullable=True),
            _field("focus", "Focus", "text", nullable=True),
            _field("experience", "Experience", "text", nullable=True),
            _field("availability_status", "Availability", "text", nullable=True),
            _field("availability_detail", "Availability details", "textarea", nullable=True),
            _field("about", "About", "textarea", nullable=True),
            _field("photo", "Profile photo", "media", asset_type="profile-image"),
        ],
    },
    "projects": {
        "label": "Projects",
        "kind": "collection",
        "write": "entries",
        "content_type": "project",
        "create_queue": ["slug", "title", "blurb"],
        "subs": ["technologies", "repositories"],
        "fields": ENTRY_FIELDS
        + [
            _field("card_image", "Card image", "media", asset_type="project-image", role="card"),
            _field("gallery", "Gallery images", "media", asset_type="project-media", role="gallery"),
        ],
    },
    "articles": {
        "label": "Articles",
        "kind": "collection",
        "write": "entries",
        "content_type": "article",
        "create_queue": ["slug", "title", "blurb"],
        "fields": ENTRY_FIELDS,
    },
    "hackathons": {
        "label": "Hackathons",
        "kind": "collection",
        "write": "entries",
        "content_type": "hackathon",
        "create_queue": ["slug", "title", "blurb"],
        "fields": ENTRY_FIELDS,
    },
    "events": {
        "label": "Events",
        "kind": "collection",
        "write": "entries",
        "content_type": "event",
        "create_queue": ["slug", "title", "blurb"],
        "fields": ENTRY_FIELDS,
    },
    "links": {
        "label": "Contact links",
        "kind": "collection",
        "write": "links",
        "create_queue": ["name", "url", "category"],
        "fields": [
            _field("name", "Name", "text"),
            _field("url", "URL", "url"),
            _field("label", "Label", "text", nullable=True),
            _field("handle", "Handle", "text", nullable=True),
            _field("category", "Category", "select", options=["professional", "social", "contact"]),
            _field("custom_order", "List order", "int"),
            _field("is_visible", "Visible", "bool"),
        ],
    },
    "skills": {
        "label": "Skill groups",
        "kind": "collection",
        "write": "skills",
        "create_queue": ["category", "skills"],
        "fields": [
            _field("category", "Category", "text"),
            _field("skills", "Skills", "tags"),
            _field("custom_order", "List order", "int"),
            _field("is_visible", "Visible", "bool"),
        ],
    },
    "education": {
        "label": "Education",
        "kind": "collection",
        "write": "education",
        "create_queue": ["degree", "school"],
        "fields": [
            _field("degree", "Degree", "text"),
            _field("school", "School", "text"),
            _field("location", "Location", "text", nullable=True),
            _field("period", "Period", "text", nullable=True),
            _field("custom_order", "List order", "int"),
        ],
    },
    "bucket-list": {
        "label": "Bucket list",
        "kind": "collection",
        "write": "bucket-list",
        "create_queue": ["title"],
        "fields": [
            _field("title", "Title", "text"),
            _field("remark", "Remark", "textarea", nullable=True),
            _field("done", "Done", "bool"),
            _field("custom_order", "List order", "int"),
        ],
    },
    "certificates": {
        "label": "Certificates",
        "kind": "collection",
        "write": "certificates",
        "no_create": True,  # created via /upload certificate <title>
        "fields": [
            _field("title", "Title", "text"),
            _field("image_url", "Image URL", "url"),
            _field("custom_order", "List order", "int"),
            _field("is_visible", "Visible", "bool"),
        ],
    },
}

RESOURCE_ORDER = [
    "profile",
    "projects",
    "articles",
    "hackathons",
    "events",
    "links",
    "skills",
    "education",
    "bucket-list",
    "certificates",
]


def field_by_key(resource_key: str, field_key: str) -> dict | None:
    for field in RESOURCES.get(resource_key, {}).get("fields", []):
        if field["key"] == field_key:
            return field
    return None


def record_label(resource_key: str, record: dict) -> str:
    spec = RESOURCES[resource_key]
    if spec.get("write") == "entries":
        return record.get("title") or record.get("slug") or "Untitled"
    return (
        record.get("title")
        or record.get("name")
        or record.get("category")
        or record.get("degree")
        or record.get("label")
        or "Record"
    )


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested without aiogram)
# ---------------------------------------------------------------------------


def parse_callback(data: str) -> tuple[str, list[str]]:
    parts = (data or "").split(":")
    if not parts or parts[0] != "mng":
        return ("unknown", [])
    return (parts[1], parts[2:])


def truncate(value: str, limit: int = MAX_BUTTON_TEXT) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def format_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return ", ".join(f"{key}: {item}" for key, item in value.items())
    return str(value)


def validate_value(field: dict, raw: str) -> tuple:
    """Return (normalized_value, error_text); error_text is None on success."""
    ftype = field["type"]
    if ftype == "text":
        value = (raw or "").strip()
        if not value:
            return (None, "The value can't be empty.")
        if len(value) > MAX_TEXT_VALUE:
            return (None, f"Keep it under {MAX_TEXT_VALUE} characters.")
        return (value, None)
    if ftype == "textarea":
        value = (raw or "").strip()
        if not value:
            return (None, "The value can't be empty.")
        if len(value) > MAX_TEXTAREA_VALUE:
            return (None, f"Keep it under {MAX_TEXTAREA_VALUE} characters.")
        return (value, None)
    if ftype == "url":
        value = (raw or "").strip()
        if not re.match(r"^https?://\S+$", value):
            return (None, "That doesn't look like a URL. It must start with http:// or https://.")
        return (value, None)
    if ftype == "slug":
        value = re.sub(r"\s+", "-", (raw or "").strip().lower())
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            return (None, "Use only lowercase letters, numbers and single hyphens, e.g. my-cool-app.")
        return (value, None)
    if ftype == "date":
        value = (raw or "").strip()
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return (None, "Use YYYY-MM-DD, e.g. 2024-06-01.")
        return (value, None)
    if ftype == "year":
        value = (raw or "").strip()
        if not value.isdigit():
            return (None, "Send a year as digits, e.g. 2024.")
        year = int(value)
        if not 1900 <= year <= 2200:
            return (None, "The year must be between 1900 and 2200.")
        return (year, None)
    if ftype == "int":
        value = (raw or "").strip()
        if not re.fullmatch(r"-?\d+", value):
            return (None, "Send a whole number.")
        return (int(value), None)
    if ftype == "tags":
        parts = [part.strip() for part in re.split(r"[,;\n]+", raw or "") if part.strip()]
        if not parts:
            return (None, "Send at least one tag.")
        seen, cleaned = set(), []
        for part in parts:
            if part not in seen:
                seen.add(part)
                cleaned.append(part)
        return (cleaned, None)
    if ftype == "select":
        value = (raw or "").strip()
        options = field.get("options") or []
        if options and value not in options:
            return (None, "Pick one of: " + ", ".join(options))
        return (value, None)
    if ftype == "bool":
        normalized = (raw or "").strip().lower()
        if normalized in ("yes", "y", "true", "1", "on", "done", "ok"):
            return (True, None)
        if normalized in ("no", "n", "false", "0", "off", "skip"):
            return (False, None)
        return (None, "Say yes or no, or use the buttons.")
    return ((raw or "").strip(), None)


def page_records(records: list, page: int, size: int = PAGE_SIZE) -> tuple[list, int, int]:
    """Return (slice, page, page_count) with bounds clamped."""
    total = len(records)
    pages = max(1, (total + size - 1) // size)
    page = max(0, min(page or 0, pages - 1))
    start = page * size
    return (records[start : start + size], page, pages)


def advance_create_queue(session: dict) -> None:
    queue = session.get("create_queue") or []
    if queue:
        queue.pop(0)
    if queue:
        session["pending_field"] = queue[0]
        session["step"] = "create"
    else:
        session.pop("create_queue", None)
        session["step"] = "field"


def build_finish_ops(session: dict) -> list[dict]:
    """Translate a session into backend operations ({resource, action, id, payload})."""
    spec = RESOURCES[session["resource"]]
    pending = dict(session.get("pending") or {})
    record_id = (session.get("record") or {}).get("id")
    if session.get("mode") == "create":
        payload = dict(pending)
        if spec.get("write") == "entries":
            payload["content_type"] = spec["content_type"]
        return [{"resource": spec["write"], "action": "create", "id": None, "payload": payload}]
    if not pending:
        return []
    payload = dict(pending)
    action = "update"
    if record_id:
        payload["id"] = record_id
    return [{"resource": spec["write"], "action": action, "id": record_id, "payload": payload}]


def render_summary(session: dict) -> str:
    spec = RESOURCES[session["resource"]]
    pending = session.get("pending") or {}
    lines = [f"<b>{'New ' if session.get('mode') == 'create' else 'Editing '}{html.escape(spec['label'], quote=False)}</b>"]
    if session.get("record"):
        label = session["record"].get("label")
        if label:
            lines.append(html.escape(str(label), quote=False))
    if pending:
        for key, value in pending.items():
            field = field_by_key(session["resource"], key)
            label = field["label"] if field else key
            changed = format_value(value)
            if value is None:
                changed = "<i>(cleared)</i>"
            lines.append(f"• {label}: <b>{html.escape(changed, quote=False)}</b>")
    elif not session.get("media_done"):
        lines.append("<i>No changes yet.</i>")
    for media_label in session.get("media_done", []):
        lines.append(f"• {html.escape(media_label, quote=False)}: ✅ attached (saved immediately)")
    return "\n".join(lines)


def field_picker_text(session: dict) -> str:
    spec = RESOURCES[session["resource"]]
    target = spec["label"]
    if session.get("record"):
        label = session["record"].get("label")
        if label:
            target = f"{spec['label']}: {label}"
    return f"<b>✏️ Manage {html.escape(target, quote=False)}</b>\nPick a field to change (✓ marks a pending change)."


def resource_keyboard() -> types.InlineKeyboardMarkup:
    rows = []
    for index in range(0, len(RESOURCE_ORDER), 2):
        row = []
        for key in RESOURCE_ORDER[index : index + 2]:
            row.append(types.InlineKeyboardButton(text=RESOURCES[key]["label"], callback_data=f"mng:res:{key}"))
        rows.append(row)
    rows.append([types.InlineKeyboardButton(text="Cancel", callback_data="mng:cancel")])
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def record_keyboard(session: dict) -> types.InlineKeyboardMarkup:
    records = session.get("records") or []
    page = session.get("records_page") or 0
    slice_records, page, pages = page_records(records, page)
    rows = [[types.InlineKeyboardButton(text="➕  Add new", callback_data="mng:create")]]
    for index, record in enumerate(slice_records, start=page * PAGE_SIZE):
        rows.append(
            [types.InlineKeyboardButton(text=truncate(record_label(session["resource"], record)), callback_data=f"mng:rec:{index}")]
        )
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(text="◀ Previous", callback_data="mng:prev"))
    if page < pages - 1:
        nav.append(types.InlineKeyboardButton(text="Next ▶", callback_data="mng:next"))
    if nav:
        rows.append(nav)
    rows.append([types.InlineKeyboardButton(text="Cancel", callback_data="mng:cancel")])
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def field_keyboard(session: dict, media: dict | None = None) -> types.InlineKeyboardMarkup:
    spec = RESOURCES[session["resource"]]
    current = session.get("current") or {}
    pending = session.get("pending") or {}
    media = media or {}
    rows = []
    for field in spec["fields"]:
        key = field["key"]
        if session.get("mode") == "create" and field["type"] == "media":
            continue
        if key in pending:
            value = format_value(pending[key]) or "empty"
            label = f"✓ {field['label']} → {truncate(value, MAX_BUTTON_TEXT - 4)}"
        else:
            hint = format_value(current.get(key))
            if not hint:
                hint = truncate(media.get(key) or "", MAX_BUTTON_TEXT - 4)
            label = field["label"] + (f": {hint}" if hint else "")
        rows.append([types.InlineKeyboardButton(text=truncate(label), callback_data=f"mng:field:{key}")])
    if session.get("mode") != "create":
        for sub in spec.get("subs", []):
            rows.append([types.InlineKeyboardButton(text=SUB_LABELS[sub], callback_data=f"mng:sub:{sub}")])
    if spec["kind"] == "collection" and session.get("mode") == "update":
        rows.append([types.InlineKeyboardButton(text="🗑  Delete this record", callback_data="mng:delete")])
    rows.append(
        [
            types.InlineKeyboardButton(text="💾 Finish & save", callback_data="mng:done"),
            types.InlineKeyboardButton(text="Cancel", callback_data="mng:cancel"),
        ]
    )
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def summary_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="✏️ Edit another field", callback_data="mng:yes")],
            [
                types.InlineKeyboardButton(text="💾 Finish & save", callback_data="mng:done"),
                types.InlineKeyboardButton(text="Cancel", callback_data="mng:cancel"),
            ],
        ]
    )


def cancel_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="Cancel", callback_data="mng:cancel")]]
    )


# ---------------------------------------------------------------------------
# Backend reads
# ---------------------------------------------------------------------------


async def fetch_media_status(session: dict) -> dict:
    statuses: dict[str, str] = {}
    spec = RESOURCES[session["resource"]]
    if spec["kind"] == "singleton":
        try:
            assets = await list_admin_resource("assets")
            statuses["photo"] = "set" if any(asset.get("asset_type") == "profile-image" for asset in assets) else "none"
        except Exception:
            statuses["photo"] = "?"
        return statuses
    record = session.get("record") or {}
    entry_id = record.get("id")
    if not entry_id:
        return statuses
    try:
        links = await list_admin_resource("entry-assets", {"entry_id": str(entry_id)})
    except Exception:
        return statuses
    roles: dict[str, int] = {}
    for link in links:
        roles[link.get("role")] = roles.get(link.get("role"), 0) + 1
    if roles.get("card"):
        statuses["card_image"] = f"{roles['card']} image(s)"
    if roles.get("gallery"):
        statuses["gallery"] = f"{roles['gallery']} image(s)"
    return statuses


def _prompt_value_text(session: dict, field: dict) -> str:
    spec = RESOURCES[session["resource"]]
    current = session.get("current") or {}
    lines = [f"<b>{field['label']}</b>"]
    if session.get("mode") == "create" and session.get("create_queue"):
        total = len(spec.get("create_queue") or [])
        done = total - len(session["create_queue"]) + 1
        lines.insert(0, f"🆕 <b>{html.escape(spec['label'], quote=False)}</b> — required field {done} of {total}")
    current_text = format_value(current.get(field["key"]))
    if current_text:
        lines.append(f"Currently: <b>{html.escape(current_text, quote=False)}</b>")
    hint = VALUE_HINTS.get(field["type"])
    if hint:
        lines.append(f"<i>{hint}</i>")
    lines.append("Send the new value, or /cancel.")
    return "\n".join(lines)


async def prompt_value(message: types.Message, session: dict, field: dict) -> None:
    await message.answer(_prompt_value_text(session, field), reply_markup=cancel_keyboard())


async def prompt_bool(message: types.Message, session: dict, field: dict) -> None:
    current = format_value((session.get("current") or {}).get(field["key"]))
    text = f"<b>{field['label']}</b>"
    if current:
        text += f"\nCurrently: <b>{html.escape(current, quote=False)}</b>"
    text += "\n\nSet it to:"
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Yes", callback_data=f"mng:bval:{field['key']}:1"),
                types.InlineKeyboardButton(text="No", callback_data=f"mng:bval:{field['key']}:0"),
            ],
            [types.InlineKeyboardButton(text="Cancel", callback_data="mng:cancel")],
        ]
    )
    await message.answer(text, reply_markup=kb)


async def prompt_select(message: types.Message, session: dict, field: dict) -> None:
    current = format_value((session.get("current") or {}).get(field["key"]))
    text = f"<b>{field['label']}</b>"
    if current:
        text += f"\nCurrently: <b>{html.escape(current, quote=False)}</b>"
    text += "\n\nChoose one:"
    options = field.get("options") or []
    rows = []
    for option in options:
        rows.append([types.InlineKeyboardButton(text=option.replace("-", " ").title(), callback_data=f"mng:sel:{field['key']}:{option}")])
    rows.append([types.InlineKeyboardButton(text="Cancel", callback_data="mng:cancel")])
    await message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=rows))


async def prompt_media(message: types.Message, field: dict) -> None:
    await message.answer(
        f"📎 <b>{field['label']}</b>\n\nSend the file as a photo or document and I'll attach it.",
        reply_markup=cancel_keyboard(),
    )


# ---------------------------------------------------------------------------
# Entry-point and session management
# ---------------------------------------------------------------------------


async def handle_manage_command(message: types.Message) -> None:
    if is_admin is not None and not is_admin(message):
        await message.answer("This command is restricted to the portfolio owner.")
        return
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) == 2:
        arg = parts[1].strip()
        start_create = False
        if arg.endswith(" new"):
            arg = arg[:-4].strip()
            start_create = True
        resource_key = ALIASES.get(arg, arg)
        if resource_key == "cancel":
            wizard_sessions.pop(message.from_user.id, None)
            await message.answer("Manage session cancelled.")
            return
        if resource_key in RESOURCES:
            await begin_resource(message, resource_key, start_create=start_create, edit=False)
            return
    wizard_sessions.pop(message.from_user.id, None)
    await message.answer("What would you like to manage?", reply_markup=resource_keyboard())


def _screen_message(target):
    """The bot Message behind a callback or a plain message."""
    return target.message if hasattr(target, "message") and target.message else target


async def begin_resource(target, resource_key: str, start_create: bool = False, edit: bool = False) -> None:
    user_id = target.from_user.id
    spec = RESOURCES[resource_key]
    session = wizard_sessions.get(user_id)
    if session is None:
        session = wizard_sessions[user_id] = {}
    session.update(
        resource=resource_key,
        mode="create" if start_create else "update",
        record=None,
        records=None,
        records_page=0,
        current={},
        pending={},
        media_done=[],
        sub=None,
        step="resource",
        pending_field=None,
    )
    screen = _screen_message(target)
    if start_create and spec.get("create_queue") and not spec.get("no_create"):
        session["create_queue"] = list(spec["create_queue"])
        session["pending_field"] = session["create_queue"][0]
        session["step"] = "create"
        field = field_by_key(resource_key, session["pending_field"])
        if field["type"] == "bool":
            await prompt_bool(screen, session, field)
        elif field["type"] == "select" and field.get("options"):
            await prompt_select(screen, session, field)
        else:
            await prompt_value(screen, session, field)
        return
    if spec["kind"] == "singleton":
        try:
            session["current"] = await get_profile()
        except Exception:
            await screen.answer("I couldn't load the profile right now. Please try again.")
            return
        session["step"] = "field"
        session["current"].setdefault("photo", None)
        await show_field_picker(screen, session, edit=edit)
        return
    try:
        records = await list_admin_resource(spec["write"], {"page_size": 200})
    except Exception:
        await screen.answer(f"I couldn't load {spec['label'].lower()} right now. Please try again.")
        return
    session["records"] = list(records or [])
    session["records_page"] = 0
    session["step"] = "record"
    text = f"<b>{html.escape(spec['label'], quote=False)}</b> — pick a record to edit, or add a new one:"
    if edit:
        await screen.edit_text(text, reply_markup=record_keyboard(session))
    else:
        await screen.answer(text, reply_markup=record_keyboard(session))


async def show_field_picker(message: types.Message, session: dict, edit: bool = False) -> None:
    media = await fetch_media_status(session)
    kb = field_keyboard(session, media)
    text = field_picker_text(session)
    if edit:
        try:
            await message.edit_text(text, reply_markup=kb)
            return
        except Exception:
            pass
    await message.answer(text, reply_markup=kb)


async def show_summary(message: types.Message, session: dict) -> None:
    await message.answer(render_summary(session), reply_markup=summary_keyboard())


# ---------------------------------------------------------------------------
# Text handlers (called from message_handlers)
# ---------------------------------------------------------------------------


async def handle_wizard_text(message: types.Message, session: dict) -> bool:
    """Consume a free-text value for the active wizard step. Returns True if handled."""
    if session.get("step") == "sub-input":
        return await handle_wizard_sub_text(message, session)
    if session.get("step") == "media":
        await message.answer("Send the file as a photo or document, or press Cancel.", reply_markup=cancel_keyboard())
        return True
    if session.get("step") not in ("value", "create"):
        return False
    field_key = session.get("pending_field") or ""
    field = field_by_key(session["resource"], field_key)
    if not field or field["type"] == "media":
        return False
    value, error = validate_value(field, message.text or "")
    if error:
        await message.answer("❌ " + error + "\n\nTry again, or /cancel.")
        return True
    session.setdefault("pending", {})[field["key"]] = value
    if session.get("step") == "create":
        advance_create_queue(session)
        if session.get("step") == "create":
            next_field = field_by_key(session["resource"], session["pending_field"])
            if next_field["type"] == "bool":
                await prompt_bool(message, session, next_field)
            elif next_field["type"] == "select" and next_field.get("options"):
                await prompt_select(message, session, next_field)
            else:
                await prompt_value(message, session, next_field)
            return True
    session["step"] = "field"
    await show_summary(message, session)
    return True


async def show_sub_panel(message: types.Message, session: dict) -> None:
    sub = session.get("sub") or {}
    kind = sub.get("kind")
    entry_id = (session.get("record") or {}).get("id")
    if kind == "technologies":
        lines = ["<b>🔧 Technologies</b>"]
        try:
            technologies = await list_admin_resource("technologies")
            links = await list_admin_resource("entry-technologies", {"entry_id": str(entry_id)}) if entry_id else []
            by_id = {str(tech.get("id")): tech.get("name") for tech in technologies}
            names = [by_id.get(str(link.get("technology_id")), "?") for link in links if link.get("technology_id")]
            lines.append("Current: " + (", ".join(html.escape(name, quote=False) for name in names) if names else "none"))
        except Exception:
            lines.append("I couldn't load the current technologies.")
        badge = "➕  Add technologies"
    elif kind == "repositories":
        lines = ["<b>📦 Repositories</b>"]
        try:
            repositories = await list_admin_resource("repositories")
            repos = [r for r in repositories if entry_id and str(r.get("entry_id")) == str(entry_id)]
            lines.append("Current: " + ("\n".join(f"• {html.escape(r.get('name') or r.get('url'), quote=False)}" for r in repos) if repos else "none"))
        except Exception:
            lines.append("I couldn't load the current repositories.")
        badge = "➕  Add repositories"
    else:
        return
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=badge, callback_data="mng:sub-add")],
            [types.InlineKeyboardButton(text="← Back to fields", callback_data="mng:sub-done")],
        ]
    )
    await message.answer("\n".join(lines), reply_markup=kb)


async def handle_wizard_sub_text(message: types.Message, session: dict) -> bool:
    if session.get("step") != "sub-input":
        return False
    sub = session.get("sub") or {}
    kind = sub.get("kind")
    entry_id = (session.get("record") or {}).get("id")
    added: list[str] = []
    text = message.text or ""
    if kind == "technologies":
        names = [name.strip() for name in re.split(r"[,;\n]+", text) if name.strip()][:20]
        if not names:
            await message.answer("Send at least one technology name, or /cancel.")
            return True
        for name in names:
            try:
                technology = await manage_content("technologies", "create", {"name": name})
                technology_id = technology.get("id")
                if technology_id and entry_id:
                    await manage_content("entry-technologies", "create", {"entry_id": str(entry_id), "technology_id": str(technology_id)})
                    added.append(name)
            except Exception:
                logger.debug("Could not link technology %s", name)
    elif kind == "repositories":
        urls = [url.strip() for url in re.split(r"[\s,;]+", text) if url.strip()][:10]
        if not urls:
            await message.answer("Send at least one repository URL, or /cancel.")
            return True
        for url in urls:
            if not re.match(r"^https?://", url):
                continue
            try:
                await manage_content("repositories", "create", {"entry_id": str(entry_id), "url": url, "synced_from_github": False})
                added.append(url)
            except Exception:
                logger.debug("Could not add repository %s", url)
    else:
        return False
    if not added:
        await message.answer("Nothing could be added — check the format and try again, or go back to fields.")
    else:
        report = "\n".join("• " + html.escape(item, quote=False) for item in added)
        await message.answer("✅ Added:\n" + report)
    session["step"] = "sub"
    await show_sub_panel(message, session)
    return True


# ---------------------------------------------------------------------------
# Callback handler (called from callback_handlers)
# ---------------------------------------------------------------------------


async def _prompt_field(message: types.Message, session: dict, field: dict) -> None:
    if field["type"] == "bool":
        await prompt_bool(message, session, field)
    elif field["type"] == "select" and field.get("options"):
        await prompt_select(message, session, field)
    else:
        await prompt_value(message, session, field)


async def finish_save(callback, session: dict) -> None:
    user_id = callback.from_user.id
    ops = build_finish_ops(session)
    if not ops:
        wizard_sessions.pop(user_id, None)
        if callback.message:
            await callback.message.edit_text("There are no pending text changes to save. (File uploads are saved immediately.)")
        return
    try:
        await callback.answer("Saving…")
    except Exception:
        pass
    try:
        for op in ops:
            await execute_admin_operation(
                op,
                update_profile=update_profile,
                manage_content=manage_content,
                bulk_manage_links=bulk_manage_links,
            )
        wizard_sessions.pop(user_id, None)
        if callback.message:
            await callback.message.edit_text("✅ Saved.")
    except httpx.HTTPStatusError as error:
        logger.exception("Wizard finish rejected by the backend")
        if callback.message:
            await callback.message.edit_text(
                f"The backend rejected the change:\n{error.response.text[:400]}\n\nYour changes are still pending — fix the value and tap Finish & save again."
            )
    except Exception:
        logger.exception("Wizard finish failed")
        if callback.message:
            await callback.message.edit_text("I couldn't save the changes. They were kept — tap Finish & save to retry.")


async def handle_wizard_callback(callback) -> None:
    user_id = callback.from_user.id
    data = callback.data or ""
    action, args = parse_callback(data)
    session = wizard_sessions.get(user_id)
    message = callback.message

    if action == "cancel":
        wizard_sessions.pop(user_id, None)
        if message:
            try:
                await message.edit_text("Cancelled.")
            except Exception:
                await callback.answer("Cancelled")
        else:
            await callback.answer("Cancelled")
        return

    if action == "res":
        resource_key = args[0] if args else ""
        if resource_key not in RESOURCES:
            await callback.answer("Unknown resource", show_alert=True)
            return
        await begin_resource(callback, resource_key, edit=True)
        return

    if session is None:
        await callback.answer("This choice has expired — start again with /manage.", show_alert=True)
        return

    if action in ("prev", "next"):
        if session.get("step") != "record":
            await callback.answer("Nothing to page here")
            return
        page = (session.get("records_page") or 0) + (1 if action == "next" else -1)
        session["records_page"] = max(0, page)
        if message:
            await message.edit_text(
                f"<b>{html.escape(RESOURCES[session['resource']]['label'], quote=False)}</b> — pick a record to edit, or add a new one:",
                reply_markup=record_keyboard(session),
            )
        return

    if action == "rec":
        try:
            index = int(args[0])
        except (TypeError, ValueError):
            index = -1
        records = session.get("records") or []
        if index < 0 or index >= len(records):
            await callback.answer("That record is no longer in the list — pick again.", show_alert=True)
            return
        record = records[index]
        session["record"] = {"id": record.get("id"), "label": truncate(record_label(session["resource"], record), 60)}
        session["current"] = record
        session["mode"] = "update"
        session["pending"] = {}
        session["media_done"] = []
        session["step"] = "field"
        await show_field_picker(message, session, edit=True)
        return

    if action == "create":
        spec = RESOURCES[session["resource"]]
        if spec.get("no_create") or not spec.get("create_queue"):
            await callback.answer("This type is created with /upload certificate <title> instead.", show_alert=True)
            return
        session["mode"] = "create"
        session["record"] = None
        session["current"] = {}
        session["pending"] = {}
        session["media_done"] = []
        session["create_queue"] = list(spec["create_queue"])
        session["pending_field"] = session["create_queue"][0]
        session["step"] = "create"
        field = field_by_key(session["resource"], session["pending_field"])
        await _prompt_field(message, session, field)
        return

    if action in ("bval", "sel"):
        key = args[0] if args else ""
        field = field_by_key(session["resource"], key)
        if not field:
            await callback.answer("Unknown field", show_alert=True)
            return
        value = args[1] == "1" if action == "bval" else args[1]
        session.setdefault("pending", {})[key] = value
        if session.get("step") == "create" and key == session.get("pending_field"):
            advance_create_queue(session)
            if session.get("step") == "create":
                next_field = field_by_key(session["resource"], session["pending_field"])
                await _prompt_field(message, session, next_field)
                return
        session["step"] = "field"
        await show_summary(message, session)
        return

    if action == "field":
        key = args[0] if args else ""
        field = field_by_key(session["resource"], key)
        if not field:
            await callback.answer("Unknown field", show_alert=True)
            return
        session["pending_field"] = key
        if field["type"] == "media":
            session["step"] = "media"
            await prompt_media(message, field)
            return
        session["step"] = "value"
        await _prompt_field(message, session, field)
        return

    if action == "yes":
        session["step"] = "field"
        await show_field_picker(message, session, edit=True)
        return

    if action == "done":
        await finish_save(callback, session)
        return

    if action == "delete":
        session["step"] = "confirm_delete"
        label = (session.get("record") or {}).get("label", "this record")
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="Yes, delete", callback_data="mng:confirm-delete")],
                [types.InlineKeyboardButton(text="Cancel", callback_data="mng:cancel")],
            ]
        )
        if message:
            await message.answer(
                f"⚠️ Delete <b>{html.escape(str(label), quote=False)}</b>?\nThis cannot be undone.",
                reply_markup=kb,
            )
        return

    if action == "confirm-delete":
        spec = RESOURCES[session["resource"]]
        record_id = (session.get("record") or {}).get("id")
        if not record_id:
            await callback.answer("No record selected", show_alert=True)
            return
        try:
            await execute_admin_operation(
                {"resource": spec["write"], "action": "delete", "id": record_id, "payload": {"id": record_id}},
                update_profile=update_profile,
                manage_content=manage_content,
                bulk_manage_links=bulk_manage_links,
            )
            wizard_sessions.pop(user_id, None)
            if message:
                await message.edit_text("🗑 Deleted.")
        except httpx.HTTPStatusError as error:
            if message:
                await message.edit_text(f"The backend rejected the deletion:\n{error.response.text[:400]}")
        except Exception:
            logger.exception("Wizard deletion failed")
            if message:
                await message.edit_text("The deletion failed. Please try again.")
        return

    if action == "sub":
        kind = args[0] if args else ""
        if kind not in SUB_LABELS:
            await callback.answer("Unknown section", show_alert=True)
            return
        session["sub"] = {"kind": kind, "added": []}
        session["step"] = "sub"
        await show_sub_panel(message, session)
        return

    if action == "sub-add":
        if not session.get("sub"):
            await callback.answer("This section has expired", show_alert=True)
            return
        session["step"] = "sub-input"
        kind = session["sub"]["kind"]
        prompt = "Send the technology names, comma-separated." if kind == "technologies" else "Send repository URLs, one per line."
        await message.answer(prompt, reply_markup=cancel_keyboard())
        return

    if action == "sub-done":
        session.pop("sub", None)
        session["step"] = "field"
        await show_field_picker(message, session, edit=True)
        return

    await callback.answer("Unknown action", show_alert=True)


# ---------------------------------------------------------------------------
# Media hooks (called from uploads.py)
# ---------------------------------------------------------------------------


async def prepare_media_upload(message: types.Message, session: dict) -> None:
    """Arm pending_upload/pending_upload_target from the active media field."""
    field = field_by_key(session["resource"], session.get("pending_field") or "")
    if not field or field["type"] != "media":
        return
    user_id = message.from_user.id
    pending_upload[user_id] = (field.get("asset_type", "file"), field["label"])
    record = session.get("record") or {}
    if record.get("id"):
        pending_upload_target[user_id] = {"entry_id": record["id"], "role": field.get("role", "gallery")}


async def media_upload_complete(message: types.Message) -> None:
    """Called by uploads.py after a successful wizard-media upload."""
    user_id = message.from_user.id
    session = wizard_sessions.get(user_id)
    if not session or session.get("step") != "media":
        return
    field = field_by_key(session["resource"], session.get("pending_field") or "")
    if field:
        session.setdefault("media_done", []).append(field["label"])
    session["step"] = "field"
    await show_summary(message, session)