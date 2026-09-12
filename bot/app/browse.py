"""Deterministic, zero-LLM browsing for the public portfolio bot.

Inline-keyboard navigation backed by direct backend REST reads. A button press
never calls the LLM: it performs one HTTP read against the public portfolio API
and renders the result locally, which sidesteps Groq rate limits entirely.

Callback-data scheme (all payloads stay under Telegram's 64-byte limit; slugs
and titles are never embedded — entries are addressed by resource/page/index,
so buttons keep working after bot restarts without per-user state):

    pub:menu                          -> main menu
    pub:list:<resource>[:<page>]      -> list view (page defaults to 1)
    pub:detail:<resource>:<page>:<i>  -> one entry from that page

`pub:` is intentionally absent from is_protected_action: browsing is public.
"""

import html
import logging
import re
import time

import httpx
from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import LinkPreviewOptions

from .callbacks import acknowledge
from .config import settings
from .tools import (
    get_profile,
    list_certificates,
    list_contact_links,
    list_entries,
    list_skills,
)

logger = logging.getLogger(__name__)

PAGE_SIZE = 5
CACHE_TTL_SECONDS = 90.0
CACHE_MAX_ENTRIES = 200
MAX_BUTTON_TITLE = 30
CLIP_TITLE = 90
CLIP_BLURB = 160
CLIP_ABOUT = 1800
# Image extensions Telegram can preview inline when a bare URL is the
# first thing in a message; certificate files are PNG/JPG/WebP served
# from R2 with signed/public URLs that usually have no extension, so
# certificates are delivered as actual photos instead (see
# _show_photo_or_text). Website links are previewed via HTML parse mode
# plus LinkPreviewOptions (Telegram unfurls them automatically).
IMAGE_URL_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_PREVIEW_BYTES = 10 * 1024 * 1024

# Icons (Telegram's Noto Emoji icon font) instead of pictorial emojis.
ICONS = {
    "menu": "\ue53e",            # list icon
    "projects": "\ue36f",        # code icon
    "articles": "\ue1c9",        # document icon
    "hackathons": "\U0001F947",  # trophy icon
    "events": "\U0001F4C5",      # calendar icon
    "skills": "\U0001F396",      # medal icon
    "certificates": "\U0001F4C3",  # scroll icon
    "contact": "\ue051",         # chat icon
    "bucket": "\u2611",          # checked box icon
    "about": "\U0001F464",       # silhouette icon
    "back": "\U0001F519",        # back arrow icon
    "link": "\U0001F517",        # chain link icon
    "repo": "\U0001F5A5",        # desktop computer icon
    "open": "\U0001F4CC",        # pushpin icon
    "camera": "\U0001F4F7",      # camera icon
    "settings": "\u2699",        # gear icon
    "detail": "\U0001F4C4",      # page icon
}

# resource -> (label, entries content_type)
ENTRY_RESOURCES = {
    "projects": ("Projects", "project"),
    "articles": ("Articles", "article"),
    "hackathons": ("Hackathons", "hackathon"),
    "events": ("Events", "event"),
}
SINGLE_RESOURCES = {
    "skills": "Skills",
    "contact": "Contact",
    "certificates": "Certificates",
    "bucket": "Bucket list",
    "about": "About",
}
RESOURCE_LABELS = {resource: label for resource, (label, _content_type) in ENTRY_RESOURCES.items()}
RESOURCE_LABELS.update(SINGLE_RESOURCES)
COUNT_KEYS = {
    "projects": "projects",
    "hackathons": "hackathons",
    "events": "events",
    "certificates": "certificates",
    "bucket": "bucket_list",
}
# Menu order used by the keyboard rows and the counts summary line.
MENU_ORDER = ("projects", "articles", "hackathons", "events", "skills", "certificates", "contact", "bucket", "about")
# Icon for every menu resource and shared control (defaults keep tests
# and future resources safe when ICONS lacks a key).
RESOURCE_ICONS = {resource: ICONS.get(resource, ICONS["detail"]) for resource in MENU_ORDER}

_cache: dict[tuple, tuple[float, object]] = {}


async def cached(key: tuple, fetch):
    """Small TTL cache so repeated taps do not re-hit the backend for the same page."""
    now = time.monotonic()
    hit = _cache.get(key)
    if hit and now - hit[0] <= CACHE_TTL_SECONDS:
        return hit[1]
    value = await fetch()
    if len(_cache) > CACHE_MAX_ENTRIES:
        expired = [item_key for item_key, (stamp, _value) in _cache.items() if now - stamp > CACHE_TTL_SECONDS]
        for item_key in expired:
            _cache.pop(item_key, None)
    _cache[key] = (now, value)
    return value


def esc(value) -> str:
    return html.escape(str(value or ""), quote=False)


def clip(value, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) > limit:
        text = text[: max(1, limit - 1)].rstrip() + "…"
    return esc(text)


def display_date(entry: dict) -> str:
    date = str(entry.get("date") or "").strip()
    if date:
        return date[:10]
    return str(entry.get("year") or "").strip()


def safe_url(url) -> str | None:
    text = str(url or "").strip()
    return text if text.startswith(("http://", "https://")) else None


def menu_button() -> types.InlineKeyboardButton:
    return types.InlineKeyboardButton(text=f"{ICONS['menu']} Menu", callback_data="pub:menu")
def menu_button() -> types.InlineKeyboardButton:
    return types.InlineKeyboardButton(text="☰ Menu", callback_data="pub:menu")
def menu_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [types.InlineKeyboardButton(text=f"{RESOURCE_ICONS[resource]} {RESOURCE_LABELS[resource]}", callback_data=f"pub:list:{resource}") for resource in MENU_ORDER]


def menu_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [types.InlineKeyboardButton(text=RESOURCE_LABELS[resource], callback_data=f"pub:list:{resource}") for resource in MENU_ORDER]
    rows = [buttons[index:index + 2] for index in range(0, len(buttons), 2)]
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


async def fetch_counts() -> dict:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.get("/counts")
        response.raise_for_status()
        return response.json()


async def fetch_bucket_list() -> list[dict]:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.get("/bucket-list")
        response.raise_for_status()
        return response.json()


async def fetch_project_detail(slug: str) -> dict | None:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.get(f"/projects/{slug}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()


async def load_overview() -> tuple[dict, int]:
    """Collection counts for the menu summary: /counts plus one articles total.

    /counts does not include articles, so one extra page-1 entries read supplies
    the total through the X-Total-Count header.
    """
    try:
        counts = await cached(("counts",), fetch_counts)
    except Exception:
        logger.exception("Browse counts fetch failed")
        counts = {}
    articles_total = 0
    try:
        articles = await cached(("entries", "articles", 1), lambda: list_entries("article", 1))
        articles_total = int((articles or {}).get("total") or 0)
    except Exception:
        logger.exception("Browse articles count fetch failed")
    return counts or {}, articles_total


def format_menu_text(first_name: str | None, owner_name: str | None, counts: dict, articles_total: int) -> str:
    lines = []
    if first_name:
        lines.append(f"Hi {esc(first_name)}!")
    if owner_name:
        lines.append(f"This is <b>{esc(owner_name)}</b>'s portfolio assistant.")
    else:
        lines.append("Portfolio assistant.")
    lines.append("Browse everything with the buttons below, or just ask me a question in plain language.")
    summary = []
    for resource in MENU_ORDER:
        if resource == "articles":
            value = articles_total
        elif resource in COUNT_KEYS:
            value = (counts or {}).get(COUNT_KEYS[resource])
        else:
            value = None
        if value:
            summary.append(f"{RESOURCE_LABELS[resource]}: {value}")
    if summary:
        lines += ["", " · ".join(summary)]
    return "\n".join(lines)


async def send_menu(message: types.Message, first_name: str | None = None) -> None:
    owner_name = None
    try:
        profile = await cached(("profile",), get_profile)
        owner_name = (profile or {}).get("name")
    except Exception:
        logger.exception("Browse profile fetch failed")
    counts, articles_total = await load_overview()
    await message.answer(
        format_menu_text(first_name, owner_name, counts, articles_total),
        reply_markup=menu_keyboard(),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


async def _show(callback: types.CallbackQuery, text: str, markup: types.InlineKeyboardMarkup | None, alert: str = "Live portfolio data — no AI involved", as_new: bool = False) -> None:
    """Render a browse view. Menu/list/pagination taps edit the tapped message in place;
    detail taps pass as_new=True so every opened item stays behind in chat as a trail."""
    try:
        if callback.message:
            if as_new:
                await callback.message.answer(text, reply_markup=markup, link_preview_options=LinkPreviewOptions(is_disabled=True))
            else:
                try:
                    await callback.message.edit_text(text, reply_markup=markup, link_preview_options=LinkPreviewOptions(is_disabled=True))
                except TelegramBadRequest as error:
                    if "message is not modified" not in str(error):
                        raise
        await callback.answer(alert)
    except Exception:
        logger.exception("Browse render failed")
        await acknowledge(callback, "The portfolio service is unavailable right now. Please try again shortly.", show_alert=True, logger=logger)


def format_entry_list(label: str, entries: list[dict], page: int, total: int) -> str:
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    lines = [f"<b>{esc(label)}</b> · {total} total · page {min(max(1, page), pages)}/{pages}", ""]
    if not entries:
        lines.append(f"No {label.lower()} published yet.")
    for index, entry in enumerate(entries, 1):
        when = display_date(entry)
        heading = f"<b>{index}. {clip(entry.get('title'), CLIP_TITLE)}</b>"
        lines.append(heading + (f" · {esc(when)}" if when else ""))
        blurb = clip(entry.get("blurb"), CLIP_BLURB)
        if blurb:
            lines.append(blurb)
    return "\n".join(lines)


def entry_list_keyboard(resource: str, entries: list[dict], page: int, total: int) -> types.InlineKeyboardMarkup:
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    rows = []
    for index, entry in enumerate(entries):
        title = str(entry.get("title") or "Untitled")
        rows.append([types.InlineKeyboardButton(text=f"{index + 1}. {title[:MAX_BUTTON_TITLE]}", callback_data=f"pub:detail:{resource}:{page}:{index}")])
    navigation = []
    if page > 1:
        navigation.append(types.InlineKeyboardButton(text=f"{ICONS['back']} Prev", callback_data=f"pub:list:{resource}:{page - 1}"))
    navigation.append(menu_button())
    if page < pages:
        navigation.append(types.InlineKeyboardButton(text=f"Next {ICONS['open']}", callback_data=f"pub:list:{resource}:{page + 1}"))
    rows.append(navigation)
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def format_skills(groups: list[dict]) -> str:
    if not groups:
        return "<b>Skills</b>\n\nNo skills published yet."
    lines = ["<b>Skills</b>", ""]
    for group in groups:
        lines.append(f"<b>{clip(group.get('category'), 60)}</b>")
        lines.append(clip(", ".join(str(skill) for skill in group.get("skills") or []), 900) or "—")
        lines.append("")
    return "\n".join(lines).strip()


def simple_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(inline_keyboard=[[menu_button()]])


def format_contact(links: list[dict]) -> str:
    lines = ["<b>Contact</b>", ""]
    for link in links:
        handle = str(link.get("handle") or link.get("label") or "").strip()
        lines.append(f"<b>{clip(link.get('name'), 40)}</b>" + (f" — {clip(handle, 60)}" if handle else ""))
    return "\n".join(lines) if len(lines) > 2 else "<b>Contact</b>\n\nNo contact links published yet."


def contact_keyboard(links: list[dict]) -> types.InlineKeyboardMarkup:
    buttons = []
    for link in links:
        url = safe_url(link.get("url"))
        if url:
            buttons.append(types.InlineKeyboardButton(text=str(link.get("name") or "Link")[:24], url=url))
    rows = [buttons[index:index + 2] for index in range(0, len(buttons), 2)]
    rows.append([menu_button()])
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def format_certificates(items: list[dict]) -> str:
    lines = ["<b>Certificates</b>", ""]
    for index, item in enumerate(items, 1):
        lines.append(f"{index}. <b>{clip(item.get('title'), 80)}</b>")
    return "\n".join(lines) if items else "<b>Certificates</b>\n\nNo certificates published yet."


def certificates_keyboard(items: list[dict]) -> types.InlineKeyboardMarkup:
    rows = []
    for item in items:
        url = safe_url(item.get("image_url"))
        if url:
            rows.append([types.InlineKeyboardButton(text=f"🖼 {str(item.get('title') or 'Certificate')[:26]}", url=url)])
    rows.append([menu_button()])
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def format_bucket_list(items: list[dict]) -> str:
    done = sum(1 for item in items if item.get("done"))
    lines = [f"<b>Bucket list</b> · {done}/{len(items)} done", ""]
    for item in items:
        mark = "✅" if item.get("done") else "⬜"
        remark = clip(item.get("remark"), 100)
        lines.append(f"{mark} {clip(item.get('title'), 80)}" + (f" — <i>{remark}</i>" if remark else ""))
    return "\n".join(lines) if items else "<b>Bucket list</b>\n\nNothing published yet."


def format_about(profile: dict) -> str:
    lines = []
    name = str(profile.get("name") or "").strip()
    if name:
        lines.append(f"<b>{esc(name)}</b>")
    for field in ("tagline", "location", "focus", "experience"):
        value = str(profile.get(field) or "").strip()
        if value:
            lines.append(esc(value))
    availability = str(profile.get("availability_status") or "").strip()
    if availability:
        lines.append(f"<b>Availability:</b> {esc(availability)}")
    detail = str(profile.get("availability_detail") or "").strip()
    if detail:
        lines.append(clip(detail, 300))
    about = str(profile.get("about") or "").strip()
    if about:
        lines += ["", clip(about, CLIP_ABOUT)]
    return "\n".join(lines).strip() or "No profile published yet."


async def render_resource(resource: str, page: int) -> tuple[str, types.InlineKeyboardMarkup]:
    if resource in ENTRY_RESOURCES:
        label, content_type = ENTRY_RESOURCES[resource]
        data = await cached(("entries", resource, page), lambda: list_entries(content_type, page))
        entries = data.get("entries") or []
        total = int(data.get("total") or 0)
        return format_entry_list(label, entries, page, total), entry_list_keyboard(resource, entries, page, total)
    if resource == "skills":
        groups = await cached(("skills",), list_skills)
        return format_skills(groups), simple_keyboard()
    if resource == "contact":
        links = await cached(("links",), list_contact_links)
        return format_contact(links), contact_keyboard(links)
    if resource == "certificates":
        items = await cached(("certificates",), list_certificates)
        return format_certificates(items), certificates_keyboard(items)
    if resource == "bucket":
        items = await cached(("bucket",), fetch_bucket_list)
        return format_bucket_list(items), simple_keyboard()
    if resource == "about":
        profile = await cached(("profile",), get_profile)
        return format_about(profile or {}), simple_keyboard()
    raise ValueError(f"Unknown browse resource: {resource}")


async def handle_menu(callback: types.CallbackQuery) -> None:
    try:
        profile = await cached(("profile",), get_profile)
        counts, articles_total = await load_overview()
        text = format_menu_text(None, (profile or {}).get("name"), counts, articles_total)
    except Exception:
        logger.exception("Browse menu failed")
        await acknowledge(callback, "The portfolio service is unavailable right now. Please try again shortly.", show_alert=True, logger=logger)
        return
    await _show(callback, text, menu_keyboard())


def parse_list_callback(data: str) -> tuple[str, int]:
    parts = data.split(":")
    resource = parts[2] if len(parts) > 2 else ""
    page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
    return resource, max(1, page)


def parse_detail_callback(data: str) -> tuple[str, int, int]:
    parts = data.split(":")
    resource = parts[2] if len(parts) > 2 else ""
    page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
    index = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
    return resource, max(1, page), max(0, index)


async def handle_list(callback: types.CallbackQuery, resource: str, page: int) -> None:
    if resource not in RESOURCE_LABELS:
        await acknowledge(callback, "Unknown section", show_alert=True, logger=logger)
        return
    try:
        text, markup = await render_resource(resource, page)
    except Exception:
        logger.exception("Browse list failed: %s page %s", resource, page)
        await acknowledge(callback, "The portfolio service is unavailable right now. Please try again shortly.", show_alert=True, logger=logger)
        return
    await _show(callback, text, markup, alert=f"{RESOURCE_LABELS[resource]} — live data, no AI involved")


def format_entry_detail(label: str, entry: dict) -> str:
    lines = [f"<b>{clip(entry.get('title'), 120)}</b>"]
    when = display_date(entry)
    if when:
        lines.append(f"{esc(label)} · {esc(when)}")
    blurb = clip(entry.get("blurb"), 900)
    if blurb:
        lines += ["", blurb]
    tags = [str(tag) for tag in (entry.get("tags") or []) if str(tag).strip()]
    if tags:
        lines += ["", "Tags: " + esc(", ".join(tags[:8]))]
    return "\n".join(lines)


def entry_detail_keyboard(resource: str, page: int, entry: dict, extra_links: list[types.InlineKeyboardButton] | None = None) -> types.InlineKeyboardMarkup:
    link_buttons = list(extra_links or [])
    primary = safe_url(entry.get("url"))
    if primary and not any(button.url == primary for button in link_buttons):
        link_buttons.insert(0, types.InlineKeyboardButton(text="🔗 Open link", url=primary))
    rows = [link_buttons[start:start + 2] for start in range(0, len(link_buttons), 2)]
    rows.append([
        types.InlineKeyboardButton(text=f"◀️ Back to {RESOURCE_LABELS[resource]}", callback_data=f"pub:list:{resource}:{page}"),
        menu_button(),
    ])
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def format_project_detail(entry: dict, project: dict | None) -> str:
    project = project or {}
    lines = [f"<b>{clip(project.get('title') or entry.get('title'), 120)}</b>"]
    meta = [value for value in (display_date(entry), str(project.get("status") or "").strip()) if value]
    if meta:
        lines.append(" · ".join(esc(value) for value in meta))
    blurb = clip(project.get("blurb") or project.get("summary") or entry.get("blurb"), 900)
    if blurb:
        lines += ["", blurb]
    technologies = [str(name) for name in (project.get("technologies") or []) if str(name).strip()]
    if technologies:
        lines += ["", "<b>Stack:</b> " + esc(", ".join(technologies[:12]))]
    tags = [str(tag) for tag in (project.get("tags") or entry.get("tags") or []) if str(tag).strip()]
    if tags:
        lines.append("Tags: " + esc(", ".join(tags[:8])))
    return "\n".join(lines)


def project_detail_keyboard(entry: dict, project: dict | None, page: int) -> types.InlineKeyboardMarkup:
    project = project or {}
    link_buttons = []
    for repository in (project.get("repositories") or [])[:3]:
        url = safe_url(repository.get("url"))
        if url:
            name = str(repository.get("name") or repository.get("link_label") or "Repository")
            link_buttons.append(types.InlineKeyboardButton(text=f"🔗 {name[:24]}", url=url))
    fallback = safe_url((project.get("links") or {}).get("repo") or entry.get("url"))
    if fallback and not any(button.url == fallback for button in link_buttons):
        link_buttons.insert(0, types.InlineKeyboardButton(text="🔗 Repository", url=fallback))
    return entry_detail_keyboard("projects", page, entry, extra_links=link_buttons)


async def handle_detail(callback: types.CallbackQuery, resource: str, page: int, index: int) -> None:
    if resource not in ENTRY_RESOURCES:
        await acknowledge(callback, "This list has expired. Pick the section again from the menu.", show_alert=True, logger=logger)
        return
    label, content_type = ENTRY_RESOURCES[resource]
    try:
        data = await cached(("entries", resource, page), lambda: list_entries(content_type, page))
        entries = data.get("entries") or []
        if index >= len(entries):
            await acknowledge(callback, "This list has changed. Pick the section again from the menu.", show_alert=True, logger=logger)
            return
        entry = entries[index]
        if resource == "projects" and entry.get("slug"):
            try:
                project = await cached(("project", entry["slug"]), lambda: fetch_project_detail(entry["slug"]))
            except Exception:
                logger.exception("Browse project detail fetch failed: %s", entry.get("slug"))
                project = None
            text = format_project_detail(entry, project)
            markup = project_detail_keyboard(entry, project, page)
        else:
            text = format_entry_detail(label, entry)
            markup = entry_detail_keyboard(resource, page, entry)
    except Exception:
        logger.exception("Browse detail failed: %s %s/%s", resource, page, index)
        await acknowledge(callback, "The portfolio service is unavailable right now. Please try again shortly.", show_alert=True, logger=logger)
        return
    # Detail views post a fresh message instead of collapsing the tapped list,
    # so the chat keeps a visible trail of every item the user opened; the list
    # message above remains interactive. Back still collapses this message.
    await _show(callback, text, markup, alert="Opened below ⬇️", as_new=True)


async def handle_public_callback(callback: types.CallbackQuery) -> None:
    """Route a `pub:` inline callback. Public for everyone; never calls the LLM."""
    data = callback.data or ""
    if data == "pub:menu":
        await handle_menu(callback)
        return
    if data.startswith("pub:list:"):
        resource, page = parse_list_callback(data)
        await handle_list(callback, resource, page)
        return
    if data.startswith("pub:detail:"):
        resource, page, index = parse_detail_callback(data)
        await handle_detail(callback, resource, page, index)
        return
    await acknowledge(callback, "Unknown action", show_alert=True, logger=logger)




