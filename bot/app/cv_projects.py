"""Owner-only project inclusion and reviewed CV-bullet management."""

import html
import logging
import re
import secrets

from aiogram import types

logger = logging.getLogger(__name__)
PAGE_SIZE = 5


def _context_tag(context: dict) -> str:
    return str(context.get("revision") or "")[:16]


def _project_callback(action: str, context: dict, index: int | None = None) -> str:
    suffix = f":{index}" if index is not None else ""
    return f"cvp:{action}:{_context_tag(context)}{suffix}"


def _is_conflict(error: Exception) -> bool:
    return getattr(getattr(error, "response", None), "status_code", None) == 409


def configure(dependencies):
    globals().update(dependencies)


def _project_key(project: dict) -> str:
    identity = project.get("id") or project.get("slug")
    if identity:
        return str(identity)
    return re.sub(r"[^a-z0-9]+", "-", str(project.get("name", "")).lower()).strip("-")


def _base_project_index(data: dict) -> dict[str, dict]:
    return {
        _project_key(project): project
        for project in data.get("projects", [])
        if isinstance(project, dict)
    }


def _find_cv_project(data: dict, source: dict) -> dict | None:
    key = _project_key(source)
    indexed = _base_project_index(data)
    if key in indexed:
        return indexed[key]
    name = str(source.get("name", "")).casefold()
    return next((item for item in data.get("projects", []) if str(item.get("name", "")).casefold() == name), None)


def _copy_source_project(source: dict) -> dict:
    stack = source.get("stack") or []
    if isinstance(stack, list):
        stack = ", ".join(str(item) for item in stack)
    return {
        "id": _project_key(source),
        "name": str(source.get("name") or ""),
        "date": str(source.get("date") or ""),
        "stack": stack,
        "bullets": list(source.get("evidence") or [])[:3],
    }


def _status_text(included: bool) -> str:
    return "In approved CV" if included else "Available to add"


def _list_markup(projects: list[dict], data: dict, page: int, context: dict):
    buttons = []
    start = page * PAGE_SIZE
    for index, project in enumerate(projects[start:start + PAGE_SIZE], start):
        included = _find_cv_project(data, project) is not None
        state = "✅" if included else "➕"
        visibility = " · hidden" if not project.get("is_visible") else ""
        title = str(project.get("name") or "Untitled project")
        buttons.append([InlineKeyboardButton(
            text=f"{state} {title[:38]}{visibility}"[:55],
            callback_data=_project_callback("open", context, index),
        )])
    navigation = []
    if page > 0:
        navigation.append(InlineKeyboardButton(text="‹ Previous", callback_data=_project_callback("list", context, page - 1)))
    if start + PAGE_SIZE < len(projects):
        navigation.append(InlineKeyboardButton(text="Next ›", callback_data=_project_callback("list", context, page + 1)))
    if navigation:
        buttons.append(navigation)
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None


def _detail_text(project: dict, cv_project: dict | None) -> str:
    title = html.escape(str(project.get("name") or "Untitled project"))
    visibility = "Public" if project.get("is_visible") else "Hidden from public portfolio"
    featured = " · Featured" if project.get("featured") else ""
    lines = [f"<b>{title}</b>", html.escape(f"{_status_text(cv_project is not None)} · {visibility}{featured}")]
    if project.get("date"):
        lines.append("Date: " + html.escape(str(project["date"])))
    description = str(project.get("description") or "").strip()
    if description:
        lines.extend(["", "<b>Project description</b>", html.escape(description[:900])])
    if project.get("stack"):
        lines.extend(["", "<b>Technology stack</b>", html.escape(", ".join(map(str, project["stack"][:16])))])
    if project.get("evidence"):
        lines.extend(["", "<b>Available evidence</b>"])
        lines.extend("• " + html.escape(str(item)[:280]) for item in project["evidence"][:4])
    if cv_project:
        lines.extend(["", "<b>Approved CV bullets</b>"])
        lines.extend("• " + html.escape(str(item)[:300]) for item in cv_project.get("bullets", [])[:3])
        if not cv_project.get("bullets"):
            lines.append("No bullets saved yet.")
    return "\n".join(lines)


def _detail_markup(index: int, page: int, included: bool, context: dict):
    action = "remove" if included else "include"
    label = "Remove from base CV" if included else "Include in base CV"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=_project_callback(action, context, index))],
        [InlineKeyboardButton(text="Draft CV bullets", callback_data=_project_callback("draft", context, index))],
        [InlineKeyboardButton(text="‹ Back to projects", callback_data=_project_callback("list", context, page))],
    ])


def _bullet_review_text(project: dict, bullets: list[str], needs_more_detail: str = "") -> str:
    lines = [f"<b>Review draft bullets · {html.escape(str(project.get('name') or 'Project'))}</b>", ""]
    lines.extend(f"{number}. {html.escape(bullet)}" for number, bullet in enumerate(bullets, 1))
    if project.get("evidence"):
        lines.extend(["", "<b>Source evidence</b>"])
        lines.extend("• " + html.escape(str(item)[:220]) for item in project["evidence"][:3])
    if needs_more_detail:
        lines.extend(["", "<b>More detail that could improve this:</b>", html.escape(needs_more_detail)])
    lines.extend(["", "Check every claim. You can edit these drafts before approving them."])
    return "\n".join(lines)


def _bullet_review_markup(token: str):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Approve", callback_data=f"cvp:approve:{token}"),
        InlineKeyboardButton(text="Edit", callback_data=f"cvp:edit:{token}"),
        InlineKeyboardButton(text="Discard", callback_data=f"cvp:discard:{token}"),
    ]])


async def _load_context(user_id: int, *, refresh: bool = False) -> dict:
    cached = cv_project_contexts.get(user_id)
    if cached and not refresh:
        return cached
    context = await get_cv_project_manager_context()
    cv_project_contexts[user_id] = {**context, "page": cached.get("page", 0) if cached else 0}
    return cv_project_contexts[user_id]


async def show_project_list(message, user_id: int, page: int = 0, *, edit: bool = False):
    try:
        context = await _load_context(user_id, refresh=True)
        base = await get_cv_base()
    except Exception as error:
        logger.exception("Loading CV project manager failed")
        detail = "The approved CV JSON is not configured yet. Upload it, then open /cvprojects again."
        if getattr(getattr(error, "response", None), "status_code", None) != 404:
            detail = friendly_error(error, "I couldn't load the CV project manager. Please try again.")
        if edit:
            await message.edit_text(detail)
        else:
            await message.answer(detail)
        return
    projects = context.get("projects", [])
    pages = max(1, (len(projects) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(int(page), pages - 1))
    context["page"] = page
    included = len(base["data"].get("projects", []))
    text = (
        f"<b>CV project manager</b> · {included} project(s) in the approved CV\n\n"
        "Choose a project to include or remove it, review its evidence, or draft CV bullets. "
        "Bullet drafts require your approval before saving."
    )
    markup = _list_markup(projects, base["data"], page, context)
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


async def handle_command(message: types.Message):
    if not is_admin(message):
        await message.answer("This command is restricted to the portfolio owner.")
        return
    await show_project_list(message, message.from_user.id)


async def _show_project_detail(message, user_id: int, index: int, *, page: int, base: dict | None = None):
    context = await _load_context(user_id)
    projects = context.get("projects", [])
    if index < 0 or index >= len(projects):
        await message.edit_text("That project list is out of date. Reopen /cvprojects.")
        return
    if base is None:
        base = await get_cv_base()
    project = projects[index]
    cv_project = _find_cv_project(base["data"], project)
    await message.edit_text(
        _detail_text(project, cv_project),
        reply_markup=_detail_markup(index, page, cv_project is not None, context),
    )


async def _save_project_toggle(user_id: int, project: dict, included: bool):
    base = await get_cv_base()
    data = base["data"]
    existing = _find_cv_project(data, project)
    if included and existing is None:
        data.setdefault("projects", []).append(_copy_source_project(project))
    elif not included and existing is not None:
        data["projects"] = [
            item for item in data.get("projects", [])
            if item is not existing
        ]
    else:
        return base
    validated = await validate_cv_base(data)
    context = await _load_context(user_id)
    await save_cv_project_manager(validated, base["revision"], context["revision"])
    return await get_cv_base()


async def _draft_bullets(callback, user_id: int, index: int, page: int):
    context = await _load_context(user_id)
    projects = context.get("projects", [])
    if index < 0 or index >= len(projects):
        await callback.answer("That project list is out of date. Reopen /cvprojects.", show_alert=True)
        return
    project = projects[index]
    try:
        await callback.answer("Drafting bullets from the saved project evidence…")
        if callback.message:
            await callback.message.edit_text("Drafting up to three CV bullets from the saved project evidence…")
        base = await get_cv_base()
        result = await draft_cv_project_bullets(project)
        bullets = result["bullets"]
        if not bullets:
            question = html.escape(result.get("needs_more_detail") or "Add more detail to the project description or highlights, then try again.")
            if callback.message:
                await callback.message.edit_text(
                    f"I couldn't draft a supported bullet for <b>{html.escape(project['name'])}</b>.\n\n{question}",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="Back to project", callback_data=_project_callback("open", context, index)),
                        InlineKeyboardButton(text="Project list", callback_data=_project_callback("list", context, page)),
                    ]]),
                )
            return
        token = secrets.token_hex(8)
        pending_cv_bullet_drafts[user_id] = {
            "token": token,
            "project_id": _project_key(project),
            "project_index": index,
            "project_name": project.get("name"),
            "page": page,
            "bullets": bullets,
            "needs_more_detail": result.get("needs_more_detail") or "",
            "awaiting_edit": False,
            "base_revision": base["revision"],
            "portfolio_revision": context["revision"],
        }
        if callback.message:
            await callback.message.edit_text(_bullet_review_text(project, bullets, result.get("needs_more_detail") or ""), reply_markup=_bullet_review_markup(token))
    except Exception as error:
        logger.exception("CV project bullet drafting failed")
        detail = friendly_error(error, "I couldn't draft bullets for that project.")
        if callback.message:
            await callback.message.edit_text(
                html.escape(detail),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="Back to project", callback_data=_project_callback("open", context, index)),
                    InlineKeyboardButton(text="Project list", callback_data=_project_callback("list", context, page)),
                ]]),
            )


async def handle_bullet_edit(message: types.Message) -> bool:
    """Accept owner-edited draft bullets, but keep them pending until approved."""
    user_id = message.from_user.id
    draft = pending_cv_bullet_drafts.get(user_id)
    if not draft or not draft.get("awaiting_edit"):
        return False
    lines = []
    for line in (message.text or "").splitlines():
        cleaned = re.sub(r"^\s*(?:[-*•]\s*|\d+[.)]\s*)", "", line).strip()
        if cleaned:
            lines.append(cleaned)
    if not 1 <= len(lines) <= 3 or any(not 30 <= len(line) <= 300 for line in lines):
        await message.answer("Send one to three bullets, one per line. Each bullet must be 30–300 characters. Nothing has been saved.")
        return True
    draft["bullets"] = lines
    draft["awaiting_edit"] = False
    context = await _load_context(user_id)
    project = next((item for item in context.get("projects", []) if _project_key(item) == draft["project_id"]), {"name": draft.get("project_name")})
    await message.answer(_bullet_review_text(project, lines, draft.get("needs_more_detail", "")), reply_markup=_bullet_review_markup(draft["token"]))
    return True


async def handle_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id != settings.admin_telegram_id:
        await callback.answer("This action is restricted to the portfolio owner.", show_alert=True)
        return
    data = callback.data or ""
    try:
        parts = data.split(":")
        action = parts[1] if len(parts) > 1 else ""
        if action in {"list", "open", "include", "remove", "draft"}:
            if len(parts) != 4:
                raise ValueError("Malformed project action")
            revision_tag, argument = parts[2], int(parts[3])
            context = await _load_context(user_id)
            if revision_tag != _context_tag(context):
                await callback.answer("This project list is out of date", show_alert=True)
                if callback.message:
                    await show_project_list(callback.message, user_id, edit=True)
                return
            if action == "list":
                await callback.answer()
                if callback.message:
                    await show_project_list(callback.message, user_id, argument, edit=True)
                return
            index = argument
            if index < 0 or index >= len(context.get("projects", [])):
                raise IndexError
            if action == "open":
                await callback.answer()
                if callback.message:
                    await _show_project_detail(callback.message, user_id, index, page=context.get("page", 0))
                return
            project = context["projects"][index]
            if action in {"include", "remove"}:
                await callback.answer("Saving CV project selection…")
                try:
                    updated = await _save_project_toggle(user_id, project, action == "include")
                except Exception as error:
                    if not _is_conflict(error):
                        raise
                    cv_project_contexts.pop(user_id, None)
                    if callback.message:
                        await show_project_list(callback.message, user_id, edit=True)
                        await callback.message.answer("The CV or project details changed. I refreshed the list; select the project again.")
                    return
                if callback.message:
                    await _show_project_detail(callback.message, user_id, index, page=context.get("page", 0), base=updated)
                return
            await _draft_bullets(callback, user_id, index, context.get("page", 0))
            return
        if action in {"approve", "edit", "discard"}:
            if len(parts) != 3:
                raise ValueError("Malformed bullet action")
            token = parts[2]
            draft = pending_cv_bullet_drafts.get(user_id)
            if not draft or draft.get("token") != token:
                await callback.answer("This bullet draft has expired", show_alert=True)
                return
        if data.startswith("cvp:discard:"):
            pending_cv_bullet_drafts.pop(user_id, None)
            await callback.answer("Draft discarded")
            if callback.message:
                context = await _load_context(user_id)
                await _show_project_detail(callback.message, user_id, draft.get("project_index", 0), page=context.get("page", 0))
            return
        if data.startswith("cvp:edit:"):
            draft["awaiting_edit"] = True
            await callback.answer()
            if callback.message:
                await callback.message.answer(
                    "Send one to three revised bullets, one per line (30–300 characters each). "
                    "You can edit the wording, but keep every claim supported by the source evidence."
                )
            return
        if data.startswith("cvp:approve:"):
            await callback.answer("Saving approved bullets…")
            context = await _load_context(user_id, refresh=True)
            if context.get("revision") != draft.get("portfolio_revision"):
                pending_cv_bullet_drafts.pop(user_id, None)
                if callback.message:
                    await show_project_list(callback.message, user_id, edit=True)
                    await callback.message.answer("Project evidence changed while this draft was waiting. Please draft the bullets again from the current evidence.")
                return
            project = next((item for item in context.get("projects", []) if _project_key(item) == draft["project_id"]), None)
            if not project:
                pending_cv_bullet_drafts.pop(user_id, None)
                if callback.message:
                    await callback.message.edit_text("The project is no longer available. Reopen /cvprojects.")
                return
            base = await get_cv_base()
            if base["revision"] != draft["base_revision"]:
                pending_cv_bullet_drafts.pop(user_id, None)
                if callback.message:
                    await callback.message.edit_text("The approved CV changed while this draft was waiting. Reopen /cvprojects and draft again.")
                return
            cv_project = _find_cv_project(base["data"], project)
            if cv_project is None:
                cv_project = _copy_source_project(project)
                base["data"].setdefault("projects", []).append(cv_project)
            cv_project["bullets"] = draft["bullets"][:3]
            validated = await validate_cv_base(base["data"])
            try:
                await save_cv_project_manager(validated, draft["base_revision"], draft["portfolio_revision"])
            except Exception as error:
                if not _is_conflict(error):
                    raise
                pending_cv_bullet_drafts.pop(user_id, None)
                cv_project_contexts.pop(user_id, None)
                if callback.message:
                    await show_project_list(callback.message, user_id, edit=True)
                    await callback.message.answer("The CV or project details changed while this draft was waiting. Please draft bullets again from the current data.")
                return
            pending_cv_bullet_drafts.pop(user_id, None)
            await _load_context(user_id, refresh=True)
            if callback.message:
                await callback.message.edit_text(
                    f"Saved the approved bullets for <b>{html.escape(project['name'])}</b> in the base CV.\n\nUse /menu → View CV to render it, or /apply with a job description to tailor it."
                )
            return
        await callback.answer("Unknown CV project action", show_alert=True)
    except (ValueError, IndexError, KeyError):
        if callback.message:
            await callback.message.edit_text("That project action expired. Reopen /cvprojects.")
        else:
            await callback.answer("That project action expired. Reopen /cvprojects.", show_alert=True)
    except Exception as error:
        logger.exception("CV project manager action failed")
        if callback.message:
            await callback.message.edit_text(friendly_error(error, "The CV project change failed."))
        else:
            await callback.answer(friendly_error(error, "The CV project change failed."), show_alert=True)
