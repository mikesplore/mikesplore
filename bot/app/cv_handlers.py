import html
import httpx
import re
import secrets
from aiogram import types


def configure(dependencies):
    globals().update(dependencies)
    globals().setdefault("pending_cv_sync", {})


async def manage_referees(message: types.Message):
    """List referees or prepare a reviewable change to the approved CV."""
    command = (message.text or "").partition(" ")[2].strip()
    action, _, payload = command.partition(" ")
    action = action.lower()
    if action not in {"list", "add", "remove"}:
        await message.answer(
            "Manage CV referees with:\n"
            "/referees list\n"
            "/referees add Name | Title | Organization | Email | Phone\n"
            "/referees remove Number\n"
            "You can also ask me in ordinary language to add, update, or remove a referee. I’ll show the proposed change before saving."
        )
        return
    if action != "list" and pending_cv_referee.get(message.from_user.id):
        await message.answer("A referee change is already waiting for review. Save or discard it first, or use /cancel.")
        return
    try:
        base = await get_cv_base()
        data = base["data"]
        referees = list(data.get("referees") or [])
        if action == "list":
            if not referees:
                await message.answer("No references are listed on the approved CV yet. Add one with /referees add Name | Title | Organization | Email | Phone.")
                return
            lines = ["<b>CV referees</b>"]
            for index, referee in enumerate(referees, 1):
                details = " · ".join(str(referee.get(key) or "") for key in ("title", "organization") if referee.get(key))
                contacts = " · ".join(str(referee.get(key) or "") for key in ("email", "phone") if referee.get(key))
                lines.append(f"\n{index}. <b>{html.escape(referee['name'])}</b>")
                if details:
                    lines.append(html.escape(details))
                if contacts:
                    lines.append(html.escape(contacts))
            await message.answer("\n".join(lines))
            return
        if action == "add":
            fields = [field.strip() for field in payload.split("|")]
            if len(fields) != 5 or not fields[0]:
                await message.answer("Use /referees add Name | Title | Organization | Email | Phone. Leave unused optional fields blank.")
                return
            referee = dict(zip(("name", "title", "organization", "email", "phone"), fields))
            referee = {key: value for key, value in referee.items() if value}
            if not referee.get("email") and not referee.get("phone"):
                await message.answer("Please include at least an email address or phone number for the referee.")
                return
            referees.append(referee)
            await prepare_cv_referee_proposal(message, data, referees, base["revision"], f"Add referee {referee['name']}")
            return
        else:
            try:
                index = int(payload.strip())
            except ValueError:
                await message.answer("Use /referees remove Number. Run /referees list to see the current numbering.")
                return
            if index < 1 or index > len(referees):
                await message.answer(f"Choose a reference number from 1 to {len(referees)}.")
                return
            removed = referees.pop(index - 1)
            await prepare_cv_referee_proposal(message, data, referees, base["revision"], f"Remove referee {removed['name']}")
            return
    except Exception as error:
        logger.exception("CV referee management failed")
        await message.answer(friendly_error(error, "I couldn't update the CV references. Please try again."))


async def prepare_cv_referee_operation(message: types.Message, operation: dict):
    """Build a validated referee proposal from an owner-requested LLM operation."""
    operation_payload = operation.get("payload") or {}
    action = operation.get("action")
    try:
        base = await get_cv_base()
        data = base["data"]
        referees = [dict(item) for item in (data.get("referees") or [])]
        if action == "list":
            if not referees:
                await message.answer("No referees are listed on the approved CV yet.")
                return
            lines = ["<b>CV referees</b>"]
            for index, referee in enumerate(referees, 1):
                details = " · ".join(str(referee.get(key) or "") for key in ("title", "organization", "email", "phone") if referee.get(key))
                lines.append(f"\n{index}. <b>{html.escape(str(referee.get('name') or 'Unnamed'))}</b>")
                if details:
                    lines.append(html.escape(details))
            await message.answer("\n".join(lines))
            return
        if action == "create":
            referee = operation_payload
            allowed = {"name", "title", "organization", "email", "phone"}
            if not isinstance(referee, dict) or set(referee) - allowed:
                raise ValueError("I could not safely identify the referee details. Please give name, role, organization, and a contact method.")
            referee = {key: str(value).strip() for key, value in referee.items() if value is not None and str(value).strip()}
            if not referee.get("name") or not (referee.get("email") or referee.get("phone")):
                raise ValueError("Please provide the referee’s name and an email address or phone number.")
            referees.append(referee)
            label = f"Add referee {referee['name']}"
        elif action in {"update", "delete"}:
            number = int(operation_payload.get("number", 0))
            if number < 1 or number > len(referees):
                raise ValueError("I couldn’t resolve that referee. Run /referees list and specify the exact name.")
            target = referees[number - 1]
            if action == "delete":
                removed = referees.pop(number - 1)
                label = f"Remove referee {removed.get('name', 'referee')}"
            else:
                fields = operation_payload.get("fields") or {}
                allowed = {"name", "title", "organization", "email", "phone"}
                if not isinstance(fields, dict) or not fields or set(fields) - allowed:
                    raise ValueError("Please specify the referee fields you want changed.")
                for key, value in fields.items():
                    if value is None or not str(value).strip():
                        target.pop(key, None)
                    else:
                        target[key] = str(value).strip()
                label = f"Update referee {target.get('name', 'referee')}"
        else:
            raise ValueError("I couldn't identify the referee change. Try asking me to add, update, or remove a referee.")
        data["referees"] = referees
        await prepare_cv_referee_proposal(message, data, referees, base["revision"], label)
    except Exception as error:
        logger.exception("CV referee proposal failed")
        await message.answer(friendly_error(error, "I couldn't prepare a referee change. Please try again."))


async def prepare_cv_referee_proposal(message, data: dict, referees: list[dict], revision: str, label: str):
    data = dict(data)
    data["referees"] = referees
    validated = await validate_cv_base(data)
    token = secrets.token_urlsafe(6)
    pending_cv_referee[message.from_user.id] = {"data": validated, "base_revision": revision, "token": token}
    lines = [f"<b>{html.escape(label)}</b>", ""]
    for index, referee in enumerate(referees, 1):
        fields = " · ".join(str(referee.get(key) or "") for key in ("title", "organization", "email", "phone") if referee.get(key))
        lines.append(f"{index}. <b>{html.escape(str(referee.get('name') or 'Unnamed'))}</b>")
        if fields:
            lines.append(html.escape(fields))
    lines.append("\nReview the complete referee list before saving.")
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Save referee changes", callback_data=f"cv-referee:save:{token}"),
        InlineKeyboardButton(text="Discard", callback_data=f"cv-referee:cancel:{token}"),
    ]]))


async def prepare_cv_patch(message: types.Message, job_description: str, revision: str | None = None):
    status = await message.answer("Analyzing the job description…")
    try:
        await status.edit_text("Searching relevant projects and skills…")
        current = pending_cv.get(message.from_user.id)
        context = await get_cv_tailoring_context()
        patch = await tailor_cv(job_description, current[0] if current else None, revision, context=context)
        # Keep only the backend contract fields. This also protects rendering
        # from provider-added metadata such as confidence or explanations.
        if patch.get("status") != "rejected":
            patch = {
                "summary": {key: str(patch.get("summary", {}).get(key, "")) for key in ("old", "new")},
                "selected_projects": [str(item) for item in patch.get("selected_projects", [])],
                "selected_skills": {
                    str(category): [str(item) for item in items]
                    for category, items in (patch.get("selected_skills") or {}).items()
                },
            }
        if patch.get("status") == "rejected":
            await status.edit_text("I won't create a tailored CV for this job.\n\n" + html.escape(patch.get("reason", "There is not enough verified portfolio evidence for this role.")))
            return
        cv_name = (context.get("profile") or {}).get("name") or "Tailored CV"
        token = secrets.token_hex(8)
        pending_cv[message.from_user.id] = (patch, job_description, cv_name, context["revision"])
        pending_cv_tokens[message.from_user.id] = token
        # The LLM may already have streamed a short preflight message and the
        # temporary status message may be stale by the time tailoring finishes.
        # Send the proposal as a fresh message so it is always visible and
        # approval is unambiguously based on this exact pending patch.
        await status.edit_text("Analysis complete. I’ve prepared a proposed CV below.")
        await message.answer(
            "Proposed CV changes:\n\n" + format_cv_patch(patch),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Generate CV", callback_data=f"cv:generate:{token}"),
                InlineKeyboardButton(text="Request changes", callback_data=f"cv:revise:{token}"),
            ]]),
        )
    except Exception as error:
        logger.exception("CV patch preparation failed")
        await status.edit_text(friendly_error(error, "I couldn't prepare a CV proposal from the current portfolio data."))


async def deliver_certificates(message: types.Message, query: str = ""):
    items = await list_certificates()
    query = query.lower()
    selected = [item for item in items if query and (query in item["title"].lower() or any(word in item["title"].lower().split() for word in query.split() if len(word) > 2))] if query else items
    selected = selected or items
    await message.answer(f"I found {len(selected)} certificate(s). Sending them directly:")
    for item in selected:
        image_url = item.get("image_url")
        if image_url:
            async with httpx.AsyncClient(timeout=20) as client:
                file_response = await client.get(image_url)
                file_response.raise_for_status()
            filename = image_url.rstrip("/").rsplit("/", 1)[-1] or "certificate"
            await message.answer_document(types.BufferedInputFile(file_response.content, filename=filename), caption=html.escape(item["title"], quote=False))


async def send_cv(message: types.Message):
    status = await message.answer("Rendering the approved CV…")
    try:
        generated = await render_base_cv()
        async with httpx.AsyncClient(timeout=30) as client:
            file_response = await client.get(generated["pdf_url"])
            file_response.raise_for_status()
    except httpx.HTTPStatusError as error:
        logger.exception("Approved CV rendering failed")
        if error.response.status_code == 404:
            await status.edit_text("There is no approved CV JSON yet. Upload the curated JSON file, then use /synccv to propose updates.")
            return
        await status.edit_text("I couldn't render the approved CV right now. Please try again shortly.")
        return
    except Exception:
        logger.exception("Approved CV rendering failed")
        await status.edit_text("I couldn't render the approved CV right now. Please try again shortly.")
        return
    if not file_response.content.startswith(b"%PDF-"):
        await status.edit_text("The generated CV file is invalid or unavailable.")
        return
    await status.edit_text("Here is the approved CV, rendered from its current JSON data.")
    await message.answer_document(types.BufferedInputFile(file_response.content, filename="Current-Portfolio-CV.pdf"), caption="Approved portfolio CV")


def _compact(value, limit=180):
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


def format_cv_sync_diff(old: dict, new: dict) -> str:
    """Create a review diff locally so the approval text reflects actual JSON changes."""
    lines = ["<b>Proposed CV JSON updates</b>"]
    scalar_fields = ("name", "title", "summary")
    for field in scalar_fields:
        if old.get(field) != new.get(field):
            lines.append(f"\n<b>{html.escape(field.title())}</b>")
            lines.append(f"Before: {html.escape(_compact(old.get(field)), quote=False)}")
            lines.append(f"After: {html.escape(_compact(new.get(field)), quote=False)}")
    if old.get("contact") != new.get("contact"):
        lines.append("\n<b>Contact</b>")
        before, after = old.get("contact") or {}, new.get("contact") or {}
        for key in sorted(set(before) | set(after)):
            if before.get(key) != after.get(key):
                lines.append(f"{html.escape(key)}: {html.escape(_compact(before.get(key), 90), quote=False)} → {html.escape(_compact(after.get(key), 90), quote=False)}")
    old_profiles = {str(item.get("url")): item for item in old.get("profiles", []) if isinstance(item, dict) and item.get("url")}
    new_profiles = {str(item.get("url")): item for item in new.get("profiles", []) if isinstance(item, dict) and item.get("url")}
    added_profiles = set(new_profiles) - set(old_profiles)
    if added_profiles:
        lines.append("\n<b>Profile links</b>")
        lines.extend("Added: " + html.escape(_compact(new_profiles[url].get("name"), 100), quote=False) for url in sorted(added_profiles))
    old_projects = {str(item.get("id") or item.get("name")): item for item in old.get("projects", []) if isinstance(item, dict)}
    new_projects = {str(item.get("id") or item.get("name")): item for item in new.get("projects", []) if isinstance(item, dict)}
    added, removed = set(new_projects) - set(old_projects), set(old_projects) - set(new_projects)
    if added or removed:
        lines.append("\n<b>Projects</b>")
        lines.extend("Added: " + html.escape(_compact(new_projects[key].get("name") or key, 100), quote=False) for key in sorted(added))
        lines.extend("Removed: " + html.escape(_compact(old_projects[key].get("name") or key, 100), quote=False) for key in sorted(removed))
    changed_projects = []
    for key in sorted(set(old_projects) & set(new_projects)):
        before, after = old_projects[key], new_projects[key]
        changed_fields = [field for field in ("date", "stack", "bullets") if before.get(field) != after.get(field)]
        if changed_fields:
            changed_projects.append((key, after, changed_fields))
    if changed_projects:
        lines.append("\n<b>Project edits</b>")
        for _key, project, fields in changed_projects[:10]:
            lines.append(html.escape(_compact(project.get("name"), 100), quote=False) + ": " + ", ".join(fields))
            if "bullets" in fields:
                for bullet in (project.get("bullets") or [])[:3]:
                    lines.append("• " + html.escape(_compact(bullet, 160), quote=False))
    for field in ("skills", "certifications", "education"):
        if old.get(field) != new.get(field):
            before, after = old.get(field) or [], new.get(field) or []
            lines.append(f"\n<b>{field.title()}</b>: {len(before)} → {len(after)} items")
            if field == "certifications":
                old_set, new_set = set(map(str, before)), set(map(str, after))
                lines.extend("Added: " + html.escape(item, quote=False) for item in sorted(new_set - old_set)[:5])
                lines.extend("Removed: " + html.escape(item, quote=False) for item in sorted(old_set - new_set)[:5])
    if old == new:
        return "No verified updates were found. The approved CV JSON is already current."
    rendered = "\n".join(lines)
    if len(rendered) <= 3600:
        return rendered
    return rendered[:3500] + "\n… diff truncated"


async def prepare_cv_sync(message: types.Message):
    if pending_cv_sync.get(message.from_user.id):
        await message.answer("A CV sync proposal is already waiting for approval. Use its Save or Discard button, or /cancel it first.")
        return
    status = await message.answer("Comparing the approved CV with current portfolio data…")
    try:
        base = await get_cv_base()
        portfolio = await get_cv_portfolio_context()
        await status.edit_text("Checking the portfolio evidence with Groq…")
        proposal = await sync_cv_data(base["data"], portfolio["data"])
        candidate = proposal["candidate"]
        if set(candidate) - set(base["data"]) - {"profiles"} or set(base["data"]) - set(candidate):
            raise ValueError("The CV sync proposal changed the CV JSON shape. No changes were saved.")
        candidate = await validate_cv_base(candidate)
        diff = format_cv_sync_diff(base["data"], candidate)
        if candidate == base["data"]:
            await status.edit_text("No verified updates were found. The approved CV JSON is already current.")
            return
        token = secrets.token_hex(8)
        pending_cv_sync[message.from_user.id] = {
            "data": candidate,
            "base_revision": base["revision"],
        "portfolio_revision": proposal["portfolio_revision"],
            "token": token,
        }
        await status.edit_text(diff, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Save CV updates", callback_data=f"cv-sync:save:{token}"),
            InlineKeyboardButton(text="Discard", callback_data=f"cv-sync:cancel:{token}"),
        ]]))
    except httpx.HTTPStatusError as error:
        logger.exception("CV sync proposal failed")
        if error.response.status_code == 404:
            await status.edit_text("No approved CV JSON is configured. Upload the curated CV JSON file first, then run /synccv.")
        else:
            await status.edit_text("I couldn't prepare a CV sync proposal. Please check the backend and try again.")
    except Exception as error:
        logger.exception("CV sync proposal failed")
        await status.edit_text(friendly_error(error, "I couldn't prepare a CV sync proposal. Please try again shortly."))


def format_cv_patch(patch: dict) -> str:
    summary = patch.get("summary") or {}
    projects = patch.get("selected_projects") or []
    skills = patch.get("selected_skills") or {}
    project_lines = []
    for project in projects:
        label = re.sub(r"[-_]+", " ", str(project)).strip().title()
        project_lines.append(f"• {html.escape(label, quote=False)}")
    skill_lines = []
    for category, items in skills.items():
        skill_lines.append(f"{html.escape(str(category), quote=False)}: " + ", ".join(html.escape(str(item), quote=False) for item in items))
    return (
        "Proposed CV update\n\n"
        "New professional summary:\n"
        f"{html.escape(str(summary.get('new', '')), quote=False)}\n\n"
        "Projects to highlight:\n"
        f"{chr(10).join(project_lines) or '• None selected'}\n\n"
        "Skills to emphasize:\n"
        f"{chr(10).join(skill_lines) or 'None selected'}\n\n"
        "Reply with changes, or say yes to generate the tailored CV."
    )
