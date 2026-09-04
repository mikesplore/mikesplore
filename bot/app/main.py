from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from fastapi import FastAPI, Header, HTTPException, Request
import html
import httpx
import logging
import json
from .tools import list_certificates

from .config import settings
from .llm import answer
from .llm import extract_admin_operation, extract_entry, extract_job_description_from_image, extract_profile_update, extract_update, tailor_cv
from .admin import apply_sync, create_entry, delete_asset, delete_certificate, delete_entry, get_cv_base, manage_content, preview_sync, render_cv, save_cv_base, search_admin_content, update_entry, update_profile, upload_asset, upload_certificate
from .formatting import telegram_html

bot = Bot(settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dispatcher = Dispatcher()
app = FastAPI(title="Portfolio Telegram bot")
logger = logging.getLogger(__name__)
pending: dict[int, dict] = {}
awaiting_entry: set[int] = set()
pending_upload: dict[int, tuple[str, str]] = {}
pending_mutation: dict[int, tuple[str, str, dict | None]] = {}
pending_sync: dict[int, tuple[str, list[dict], list[str]]] = {}
awaiting_cv: set[int] = set()
pending_cv: dict[int, tuple[dict, str, str, str]] = {}
list_context: dict[int, tuple[str, int]] = {}
conversation_history: dict[int, list[dict[str, str]]] = {}


async def show_typing(message: types.Message) -> None:
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")


@app.on_event("startup")
async def register_commands():
    """Publish Telegram's command menu when the webhook process starts."""
    await bot.set_my_short_description(
        "Ask about the portfolio, projects, skills, and certifications."
    )
    await bot.set_my_description(
        "This is a portfolio assistant. Ask about the owner's projects, "
        "skills, writing, hackathons, certifications, education, or experience. "
        "Answers are grounded in his current portfolio data."
    )
    public_commands = [
        types.BotCommand(command="start", description="Start the portfolio assistant"),
        types.BotCommand(command="help", description="Show help"),
    ]
    admin_commands = public_commands + [
        types.BotCommand(command="add", description="Add a curated entry"),
        types.BotCommand(command="admin", description="Manage data using an instruction"),
        types.BotCommand(command="edit", description="Edit an entry"),
        types.BotCommand(command="delete", description="Delete an entry"),
        types.BotCommand(command="profile", description="Update profile text"),
        types.BotCommand(command="apply", description="Tailor CV to a job description"),
        types.BotCommand(command="cv", description="Upload the base CV JSON"),
        types.BotCommand(command="upload", description="Upload an asset or certificate"),
        types.BotCommand(command="sync", description="Fetch Dev.to or GitHub content"),
        types.BotCommand(command="manage", description="Manage portfolio collections"),
        types.BotCommand(command="delete-asset", description="Delete an uploaded asset"),
        types.BotCommand(command="delete-certificate", description="Delete a certificate"),
        types.BotCommand(command="confirm", description="Confirm a pending change"),
        types.BotCommand(command="cancel", description="Cancel a pending change"),
    ]
    await bot.set_my_commands(public_commands)
    await bot.set_my_commands(
        admin_commands,
        scope=types.BotCommandScopeChat(chat_id=settings.admin_telegram_id),
    )


def is_admin(message: types.Message) -> bool:
    return bool(message.from_user and message.from_user.id == settings.admin_telegram_id)


@dispatcher.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Ask me about the portfolio owner's projects, writing, hackathons, or events.")


@dispatcher.message(Command("help"))
async def help_command(message: types.Message):
    admin_hint = (
        "\n\nAdmin commands:\n"
        "/add — add a curated entry\n"
        "/admin &lt;instruction&gt; — create, update, or delete content\n"
        "/edit &lt;entry&gt; &lt;changes&gt; — edit an entry\n"
        "/delete &lt;entry&gt; — delete an entry\n"
        "/profile &lt;changes&gt; — update profile text\n"
        "/apply &lt;job description&gt; — propose a tailored CV patch\n"
        "/cv base — upload the source cv_data.json\n"
        "/sync devto — preview and import Dev.to articles\n"
        "/sync github — preview GitHub repositories (hidden by default)\n"
        "/sync github 1,3 — select repositories to show\n"
        "/upload &lt;asset_type&gt; [label] — upload a file\n"
        "/manage &lt;resource&gt; &lt;action&gt; [JSON] — manage other content\n"
        "/delete-asset &lt;id&gt; — delete an uploaded asset\n"
        "/delete-certificate &lt;id&gt; — delete a certificate\n"
        "/confirm — apply a pending change or sync\n"
        "/cancel — discard a pending change or sync"
        if is_admin(message) else ""
    )
    await message.answer("Public commands:\n/start — start the assistant\n/help — show this help\n\n"
                         "You can also ask questions about the portfolio owner's projects, writing, "
                         "skills, education, certificates, CV, and contact details." + admin_hint)


@dispatcher.message(Command("add"))
async def add_command(message: types.Message):
    if not is_admin(message):
        await message.answer("That command is restricted to the administrator.")
        return
    awaiting_entry.add(message.from_user.id)
    await message.answer("Send the entry instruction as text. Use /cancel to discard it.")


@dispatcher.message(Command("upload"))
async def upload_command(message: types.Message):
    if not is_admin(message):
        await message.answer("That command is restricted to the administrator.")
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Usage: /upload &lt;asset_type&gt; [label], then send a file.")
        return
    pending_upload[message.from_user.id] = (parts[1], parts[2] if len(parts) > 2 else parts[1])
    await message.answer("Send the file now (maximum size: 10 MB). Use /cancel to discard it.")


@dispatcher.message(Command("sync"))
async def sync_command(message: types.Message):
    if not is_admin(message):
        await message.answer("That command is restricted to the administrator.")
        return
    parts = (message.text or "").split(maxsplit=2)
    source = parts[1].lower() if len(parts) > 1 else ""
    if source not in {"devto", "github"}:
        await message.answer("Usage: /sync devto or /sync github")
        return
    try:
        await show_typing(message)
        result = await preview_sync(source)
        items = result["items"]
        selected = [item["source"]["key"] for item in items] if source == "devto" else []
        if source == "github" and len(parts) > 2:
            indexes = {int(value) - 1 for value in parts[2].replace(" ", "").split(",") if value.isdigit()}
            selected = [item["source"]["key"] for index, item in enumerate(items) if index in indexes]
        pending_sync[message.from_user.id] = (source, items, selected)
        lines = [f"{index + 1}. {item['title']} — {'show' if item['source']['key'] in selected else 'hide'}" for index, item in enumerate(items)]
        instruction = "Articles default to show. Send /confirm to import." if source == "devto" else "GitHub defaults to hidden. Reply /sync github 1,3 (or similar) to choose, then /confirm."
        await message.answer(f"{source.title()} sync preview ({len(items)} items):\n\n" + "\n".join(lines[:80]) + f"\n\n{instruction}")
    except Exception:
        logger.exception("%s sync preview failed", source)
        await message.answer(f"I couldn't fetch {source} right now. Check the backend source configuration.")


@dispatcher.message(Command("edit"))
async def edit_command(message: types.Message):
    if not is_admin(message):
        await message.answer("That command is restricted to the administrator.")
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /edit &lt;entry-id-or-slug&gt; &lt;changes&gt;")
        return
    try:
        await show_typing(message)
        changes = await extract_update(parts[2])
        pending_mutation[message.from_user.id] = ("edit", parts[1], changes)
        await message.answer("Edit preview (send /confirm to save, /cancel to discard):\n\n" + format_preview(changes))
    except Exception:
        await message.answer("I couldn't understand those changes.")


@dispatcher.message(Command("profile"))
async def profile_command(message: types.Message):
    if not is_admin(message):
        await message.answer("That command is restricted to the administrator.")
        return
    instruction = (message.text or "").partition(" ")[2]
    if not instruction:
        await message.answer("Usage: /profile &lt;changes&gt;")
        return
    try:
        await show_typing(message)
        changes = await extract_profile_update(instruction)
        pending_mutation[message.from_user.id] = ("profile", "profile", changes)
        await message.answer("Profile preview (send /confirm to save, /cancel to discard):\n\n" + format_preview(changes))
    except Exception:
        await message.answer("I couldn't understand those profile changes.")


@dispatcher.message(Command("cv"))
async def cv_command(message: types.Message):
    if not is_admin(message):
        await message.answer("That command is restricted to the administrator.")
        return
    action = (message.text or "").strip().lower()
    if action == "/cv base":
        pending_upload[message.from_user.id] = ("cv-json", "base")
        await message.answer("Send the source cv_data.json file now. It will replace the stored base CV JSON.")
        return
    await message.answer("Usage: /cv base (upload cv_data.json). Use /apply <job description> to tailor a CV.")


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
        pending_cv[message.from_user.id] = (patch, job_description, "Tailored CV", base["revision"])
        await status.edit_text("Preparing proposed CV changes…")
        await status.edit_text("Proposed CV changes:\n\n" + format_cv_patch(patch) + "\n\nConfirm, or tell me what to change.")
    except Exception:
        logger.exception("CV patch preparation failed")
        await status.edit_text("I couldn't prepare a valid CV patch. Please check the base CV and try again.")


@dispatcher.message(Command("apply"))
async def apply_command(message: types.Message):
    if not is_admin(message):
        await message.answer("That command is restricted to the administrator.")
        return
    job_description = (message.text or "").partition(" ")[2].strip()
    if not job_description:
        awaiting_cv.add(message.from_user.id)
        await message.answer("Send the job description now. I will propose changes for review.")
        return
    await prepare_cv_patch(message, job_description)


@dispatcher.message(Command("manage"))
async def manage_command(message: types.Message):
    if not is_admin(message):
        await message.answer("That command is restricted to the administrator.")
        return
    parts = (message.text or "").split(maxsplit=3)
    if len(parts) < 3:
        await message.answer('Usage: /manage &lt;links|skills|education|bucket-list|settings&gt; &lt;list|create|update|delete&gt; [JSON]')
        return
    import json
    resource, action = parts[1], parts[2]
    if action == "list":
        try:
            items = await manage_content(resource, action, {})
            await message.answer(format_preview({"resource": resource, "items": items})[:3900])
        except Exception:
            await message.answer("The backend rejected that list request.")
        return
    if len(parts) < 4:
        await message.answer("Create, update, and delete require a JSON payload.")
        return
    try:
        payload = json.loads(parts[3])
        pending_mutation[message.from_user.id] = ("manage", f"{resource}:{action}", payload)
        await message.answer("Management preview (send /confirm to save, /cancel to discard):\n\n" + format_preview({"resource": resource, "action": action, **payload}))
    except Exception:
        await message.answer("The resource, action, or JSON payload is invalid.")


@dispatcher.message(Command("admin"))
async def admin_command(message: types.Message):
    if not is_admin(message):
        await message.answer("That command is restricted to the administrator.")
        return
    instruction = (message.text or "").partition(" ")[2].strip()
    if not instruction:
        await message.answer("Usage: /admin &lt;instruction&gt;")
        return
    try:
        await show_typing(message)
        candidates = await search_admin_content(instruction)
        operation = await extract_admin_operation(instruction, candidates)
        if operation.get("action") is None:
            await message.answer("I found multiple possible records. Please make the instruction more specific:\n\n" + format_preview({"candidates": candidates}))
            return
        pending_mutation[message.from_user.id] = ("admin", operation["resource"] + ":" + operation["action"], operation)
        await message.answer("Admin preview (send /confirm to save, /cancel to discard):\n\n" + format_preview(operation))
    except Exception:
        await message.answer("I couldn't translate that into a safe database operation. Include the exact record ID for updates or deletes.")


@dispatcher.message(Command("delete"))
async def delete_command(message: types.Message):
    if not is_admin(message):
        await message.answer("That command is restricted to the administrator.")
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /delete &lt;entry-id-or-slug&gt;")
        return
    pending_mutation[message.from_user.id] = ("delete", parts[1], None)
    await message.answer(f"Delete entry {html.escape(parts[1], quote=False)}? Send /confirm to delete or /cancel to abort.")


@dispatcher.message(Command("delete-asset"))
async def delete_asset_command(message: types.Message):
    if not is_admin(message):
        await message.answer("That command is restricted to the administrator.")
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /delete-asset &lt;asset-id&gt;")
        return
    pending_mutation[message.from_user.id] = ("asset-delete", parts[1], None)
    await message.answer(f"Delete asset {html.escape(parts[1], quote=False)}? Send /confirm to delete or /cancel to abort.")


@dispatcher.message(Command("delete-certificate"))
async def delete_certificate_command(message: types.Message):
    if not is_admin(message):
        await message.answer("That command is restricted to the administrator.")
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /delete-certificate &lt;certificate-id&gt;")
        return
    pending_mutation[message.from_user.id] = ("certificate-delete", parts[1], None)
    await message.answer(f"Delete certificate {html.escape(parts[1], quote=False)}? Send /confirm to delete or /cancel to abort.")


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


@dispatcher.message(lambda message: not message.document and not message.photo)
async def question(message: types.Message):
    if is_admin(message) and message.text:
        if message.text.strip().lower() in {"/cancel", "cancel"}:
            pending.pop(message.from_user.id, None)
            awaiting_entry.discard(message.from_user.id)
            pending_mutation.pop(message.from_user.id, None)
            pending_sync.pop(message.from_user.id, None)
            awaiting_cv.discard(message.from_user.id)
            pending_cv.pop(message.from_user.id, None)
            await message.answer("Cancelled.")
            return
        if message.text.strip().lower() in {"/confirm", "confirm"}:
            sync = pending_sync.pop(message.from_user.id, None)
            if sync:
                try:
                    result = await apply_sync(sync[0], sync[1], sync[2])
                    await message.answer(f"{sync[0].title()} sync complete: {result['updated']} entries upserted.")
                except Exception:
                    pending_sync[message.from_user.id] = sync
                    logger.exception("Sync apply failed")
                    await message.answer("The sync could not be completed. The preview is still pending; try /confirm again.")
                return
            tailored = pending_cv.pop(message.from_user.id, None)
            if tailored:
                try:
                    patch, job_description, label, base_revision = tailored
                    result = await render_cv(patch, base_revision, job_description, label)
                    async with httpx.AsyncClient(timeout=30) as client:
                        pdf_response = await client.get(result["pdf_url"])
                        pdf_response.raise_for_status()
                    await message.answer_document(types.BufferedInputFile(pdf_response.content, filename=f"{label}.pdf"), caption=html.escape(label, quote=False))
                except Exception:
                    pending_cv[message.from_user.id] = tailored
                    logger.exception("Tailored CV rendering failed")
                    await message.answer("The tailored CV could not be rendered. The preview is still pending; try /confirm again.")
                return
            mutation = pending_mutation.pop(message.from_user.id, None)
            if mutation:
                try:
                    if mutation[0] == "delete": await delete_entry(mutation[1])
                    elif mutation[0] == "asset-delete": await delete_asset(mutation[1])
                    elif mutation[0] == "certificate-delete": await delete_certificate(mutation[1])
                    elif mutation[0] == "profile": await update_profile(mutation[2] or {})
                    elif mutation[0] == "manage":
                        resource, action = mutation[1].split(":", 1)
                        await manage_content(resource, action, mutation[2] or {})
                    elif mutation[0] == "admin":
                        operation = mutation[2] or {}
                        resource, action = operation["resource"], operation["action"]
                        if resource == "profile":
                            await update_profile(operation.get("payload", {}))
                        else:
                            payload = dict(operation.get("payload") or {
                                key: value for key, value in operation.items()
                                if key not in {"resource", "action", "id", "candidates", "payload"}
                            })
                            if operation.get("id"):
                                payload["id"] = operation["id"]
                            await manage_content(resource, action, payload)
                    else: await update_entry(mutation[1], mutation[2] or {})
                    if mutation[0] == "profile":
                        result_message = "Profile updated."
                    elif mutation[0] == "manage":
                        result_message = "Content managed."
                    elif mutation[0] == "edit":
                        result_message = "Entry updated."
                    elif mutation[0] == "admin":
                        action = (mutation[2] or {}).get("action")
                        result_message = {"create": "Entry created.", "update": "Entry updated.", "delete": "Entry deleted."}.get(action, "Change applied.")
                    else:
                        result_message = "Entry deleted."
                    await message.answer(result_message)
                except httpx.HTTPStatusError as error:
                    logger.exception("Admin mutation rejected")
                    pending_mutation[message.from_user.id] = mutation
                    await message.answer(f"The backend rejected that change: {error.response.text[:500]}")
                except Exception:
                    logger.exception("Admin mutation failed")
                    pending_mutation[message.from_user.id] = mutation
                    await message.answer("The change could not be completed. The preview is still available; try /confirm again.")
                return
            entry = pending.pop(message.from_user.id, None)
            if not entry:
                await message.answer("There is no pending preview. File uploads are saved immediately; /confirm is only for pending edits or content changes.")
                return
            try:
                created = await create_entry(entry)
                await message.answer(f"Saved entry: {html.escape(created['title'], quote=False)}")
            except Exception:
                pending[message.from_user.id] = entry
                await message.answer("The backend rejected the entry. The preview is still pending.")
            return
        if message.from_user.id in awaiting_cv:
            awaiting_cv.discard(message.from_user.id)
            await prepare_cv_patch(message, message.text)
            return
        if message.from_user.id in pending_cv:
            patch, job_description, _label, _revision = pending_cv[message.from_user.id]
            await prepare_cv_patch(message, job_description, message.text)
            return
        if message.from_user.id in awaiting_entry:
            try:
                await show_typing(message)
                entry = await extract_entry(message.text)
                pending[message.from_user.id] = entry
                awaiting_entry.discard(message.from_user.id)
                await message.answer("Preview (send /confirm to save, /cancel to discard):\n\n" + format_preview(entry))
            except Exception:
                await message.answer("I couldn't extract a valid entry. Please provide a clearer instruction.")
            return
    try:
        await show_typing(message)
        question_text = message.text or ""
        user_id = message.from_user.id
        normalized = question_text.lower().strip()
        is_next = normalized in {"yes", "y", "next", "next page", "show more", "more"} or "next page" in normalized
        if is_next and user_id in list_context:
            content_type, current_page = list_context[user_id]
            question_text = f"Show page {current_page + 1} of {content_type}s from the portfolio."
            list_context[user_id] = (content_type, current_page + 1)
        else:
            content_type = next((value for value in ("project", "article", "hackathon", "event") if value in normalized), None)
            if content_type and any(word in normalized for word in ("show", "list", "what", "which")):
                list_context[user_id] = (content_type, 1)
        history = conversation_history.setdefault(user_id, [])
        response = await answer(question_text, history[-10:])
        history.extend([
            {"role": "user", "content": question_text},
            {"role": "assistant", "content": response},
        ])
        del history[:-10]
    except Exception:
        logger.exception("Public portfolio lookup failed")
        response = "I couldn't reach the portfolio right now. Please try again shortly."
    if response.startswith("__BOT_ACTION__"):
        action = __import__('json').loads(response.removeprefix("__BOT_ACTION__"))
        try:
            if action["action"] == "send_cv":
                await send_cv(message)
            elif action["action"] == "send_certificates":
                await deliver_certificates(message, action.get("query", ""))
        except Exception:
            logger.exception("Bot action failed")
            await message.answer("I couldn't complete that request right now. Please try again shortly.")
        return
    await message.answer(telegram_html(response))


@dispatcher.message(lambda message: bool(message.document or message.photo))
async def document(message: types.Message):
    if not is_admin(message):
        await message.answer("Document ingestion is restricted to the administrator.")
        return
    asset_type = "certificate"
    try:
        if message.from_user.id not in awaiting_cv or pending_upload.get(message.from_user.id):
            await message.answer("File received. Uploading it now…")
        await show_typing(message)
        asset_request = pending_upload.get(message.from_user.id)
        telegram_file_id = message.document.file_id if message.document else message.photo[-1].file_id
        telegram_file = await bot.get_file(telegram_file_id)
        if telegram_file.file_size and telegram_file.file_size > 10 * 1024 * 1024:
            await message.answer("That file is too large. Please send a file no bigger than 10 MB.")
            return
        buffer = __import__('io').BytesIO()
        await bot.download_file(telegram_file.file_path, buffer)
        filename = message.document.file_name if message.document else "upload.jpg"
        mime_type = message.document.mime_type if message.document else "image/jpeg"
        if message.from_user.id in awaiting_cv and not asset_request:
            if mime_type.startswith("image/"):
                await message.answer("Reading the job poster…")
                job_description = await extract_job_description_from_image(buffer.getvalue(), mime_type)
            elif mime_type == "application/pdf":
                from pypdf import PdfReader
                job_description = "\n".join(page.extract_text() or "" for page in PdfReader(buffer).pages).strip()
                if len(job_description) < 30:
                    await message.answer("That PDF has no readable text. Please send an image poster or a text-based PDF.")
                    return
            else:
                await message.answer("For a job description, send a poster image or PDF.")
                return
            awaiting_cv.discard(message.from_user.id)
            await prepare_cv_patch(message, job_description)
            return
        if asset_request:
            asset_type, label = asset_request
            if asset_type == "cv-json":
                import json
                try:
                    data = json.loads(buffer.getvalue().decode("utf-8"))
                    await save_cv_base(data)
                except Exception:
                    logger.exception("Base CV JSON upload failed")
                    await message.answer("That is not a valid CV JSON file or it failed backend validation.")
                    return
                pending_upload.pop(message.from_user.id, None)
                await message.answer("Base CV JSON saved.")
                return
            if asset_type == "certificate":
                # Certificates have their own database collection and public
                # listing endpoint. Do not store them as generic site assets.
                result = await upload_certificate(label, filename, buffer.getvalue(), mime_type)
                pending_upload.pop(message.from_user.id, None)
                await message.answer(f"Certificate uploaded: {html.escape(result['title'], quote=False)}")
                return
            result = await upload_asset(asset_type, label, filename, buffer.getvalue(), mime_type)
            pending_upload.pop(message.from_user.id, None)
            await message.answer(f"Asset uploaded: {html.escape(result['label'], quote=False)}")
            if asset_type == "profile-image":
                try:
                    await bot.set_my_profile_photo(
                        photo=types.InputProfilePhotoStatic(
                            photo=types.BufferedInputFile(buffer.getvalue(), filename=filename)
                        )
                    )
                    await message.answer("My profile image was updated too.")
                except Exception:
                    logger.exception("Telegram bot profile photo update failed")
                    await message.answer("The portfolio image was updated, but Telegram's bot profile image could not be changed.")
        else:
            result = await upload_certificate(message.caption or filename, filename, buffer.getvalue(), mime_type)
            await message.answer(f"Certificate uploaded: {html.escape(result['title'], quote=False)}")
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 413:
            await message.answer("That file is too large. Please send a file no bigger than 10 MB.")
        else:
            logger.exception("%s upload failed", asset_type)
            await message.answer(f"I couldn't upload that {asset_type}. Please check R2 configuration and try again.")
    except Exception:
        logger.exception("%s upload failed", asset_type)
        await message.answer(f"I couldn't upload that {asset_type}. Please check R2 configuration and try again.")


def format_preview(entry: dict) -> str:
    if "resource" in entry and "action" in entry and "payload" in entry:
        return "\n".join([
            f"Resource: {html.escape(str(entry.get('resource')), quote=False)}",
            f"Action: {html.escape(str(entry.get('action')), quote=False)}",
            f"Record ID: {html.escape(str(entry.get('id') or 'new record'), quote=False)}",
            "Changes:",
            html.escape(str(entry.get("payload") or "—"), quote=False),
        ])
    if "candidates" in entry:
        return "\n".join(f"{candidate.get('resource')}: {candidate.get('record')}" for candidate in entry["candidates"])
    fields = ("resource", "action", "id", "title", "content_type", "blurb", "date", "year", "tech_stack", "tags", "links", "payload", "candidates")
    return "\n".join(f"{field}: {html.escape(str(entry.get(field) or '—'), quote=False)}" for field in fields)


def format_cv_patch(patch: dict) -> str:
    summary = patch.get("summary") or {}
    projects = patch.get("selected_projects") or []
    skills = patch.get("selected_skills") or {}
    return (
        f"Summary old:\n{html.escape(str(summary.get('old', '')))}\n\n"
        f"Summary new:\n{html.escape(str(summary.get('new', '')))}\n\n"
        f"Selected project IDs: {', '.join(html.escape(str(item)) for item in projects) or 'none'}\n"
        f"Selected skills:\n{html.escape(json.dumps(skills, indent=2))}"
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/telegram/webhook")
async def webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    await dispatcher.feed_update(bot, types.Update.model_validate(await request.json(), context={"bot": bot}))
    return {"ok": True}
