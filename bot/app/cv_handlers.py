import html
import httpx
import re
from aiogram import types


def configure(dependencies):
    globals().update(dependencies)


async def prepare_cv_patch(message: types.Message, job_description: str, revision: str | None = None):
    status = await message.answer("Analyzing the job description…")
    try:
        await status.edit_text("Searching relevant projects and skills…")
        current = pending_cv.get(message.from_user.id)
        patch = await tailor_cv(job_description, current[0] if current else None, revision)
        if patch.get("status") == "rejected":
            await status.edit_text("I won't create a tailored CV for this job.\n\n" + html.escape(patch.get("reason", "There is not enough verified portfolio evidence for this role.")))
            return
        base = await get_cv_base()
        cv_name = (base.get("data") or {}).get("name") or "Tailored CV"
        pending_cv[message.from_user.id] = (patch, job_description, cv_name, base["revision"])
        await status.edit_text("Preparing proposed CV changes…")
        await status.edit_text("Proposed CV changes:\n\n" + format_cv_patch(patch), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Generate CV", callback_data="cv:generate"), InlineKeyboardButton(text="Request changes", callback_data="cv:revise")]]))
    except Exception as error:
        logger.exception("CV patch preparation failed")
        await status.edit_text(friendly_error(error, "I couldn't prepare a valid CV patch. Please check the base CV and try again."))


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
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=20) as client:
        response = await client.get("/assets")
        response.raise_for_status()
        cv = next((asset for asset in response.json() if asset.get("asset_type") == "cv"), None)
        if not cv:
            await message.answer("The base CV is not available right now.")
            return
        file_response = await client.get(cv["url"])
        file_response.raise_for_status()
    if not file_response.content.startswith(b"%PDF-"):
        await message.answer("The stored CV file is invalid or unavailable.")
        return
    filename = cv.get("label") or "CV.pdf"
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    await message.answer_document(types.BufferedInputFile(file_response.content, filename=filename), caption="CV")


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
