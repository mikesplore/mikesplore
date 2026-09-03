from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from fastapi import FastAPI, Header, HTTPException, Request
import html
import logging
from .tools import list_certificates

from .config import settings
from .llm import answer
from .llm import extract_entry, extract_profile_update, extract_update
from .admin import create_entry, delete_entry, manage_content, update_entry, update_profile, upload_asset, upload_certificate
from .formatting import telegram_html

bot = Bot(settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dispatcher = Dispatcher()
app = FastAPI(title="mikesplore Telegram bot")
logger = logging.getLogger(__name__)
pending: dict[int, dict] = {}
awaiting_entry: set[int] = set()
pending_upload: dict[int, tuple[str, str]] = {}
pending_mutation: dict[int, tuple[str, str, dict | None]] = {}


def is_admin(message: types.Message) -> bool:
    return bool(message.from_user and message.from_user.id == settings.admin_telegram_id)


@dispatcher.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Ask me about Michael's projects, writing, hackathons, or events.")


@dispatcher.message(Command("help"))
async def help_command(message: types.Message):
    admin_hint = (
        "\n\nAdmin commands:\n"
        "/add — create an entry\n"
        "/edit &lt;entry-id&gt; &lt;changes&gt;\n"
        "/delete &lt;entry-id&gt;\n"
        "/profile &lt;changes&gt;\n"
        "/manage &lt;links|skills|education|bucket-list|settings&gt; &lt;list|create|update|delete&gt; [JSON]\n"
        "/upload &lt;asset_type&gt; [label]"
        if is_admin(message) else ""
    )
    await message.answer("Use /start, /help, or ask a question about the public portfolio." + admin_hint)


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
    await message.answer("Send the file now. Use /cancel to discard it.")


@dispatcher.message(Command("edit"))
async def edit_command(message: types.Message):
    if not is_admin(message):
        await message.answer("That command is restricted to the administrator.")
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /edit &lt;entry-id&gt; &lt;changes&gt;")
        return
    try:
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
        changes = await extract_profile_update(instruction)
        pending_mutation[message.from_user.id] = ("profile", "profile", changes)
        await message.answer("Profile preview (send /confirm to save, /cancel to discard):\n\n" + format_preview(changes))
    except Exception:
        await message.answer("I couldn't understand those profile changes.")


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


@dispatcher.message(Command("delete"))
async def delete_command(message: types.Message):
    if not is_admin(message):
        await message.answer("That command is restricted to the administrator.")
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /delete &lt;entry-id&gt;")
        return
    pending_mutation[message.from_user.id] = ("delete", parts[1], None)
    await message.answer(f"Delete entry {html.escape(parts[1], quote=False)}? Send /confirm to delete or /cancel to abort.")


@dispatcher.message(lambda message: message.text and "certificate" in message.text.lower())
async def certificates(message: types.Message):
    try:
        items = await list_certificates()
        await message.answer(f"I found {len(items)} certificates. Sending them directly:")
        for item in items:
            image_url = item.get("image_url")
            if image_url:
                await message.answer_document(types.URLInputFile(image_url), caption=html.escape(item["title"], quote=False))
    except Exception:
        logger.exception("Certificate lookup failed")
        await message.answer("I couldn't retrieve the certificates right now. Please try again shortly.")


@dispatcher.message(lambda message: not message.document)
async def question(message: types.Message):
    if is_admin(message) and message.text:
        if message.text.strip().lower() in {"/cancel", "cancel"}:
            pending.pop(message.from_user.id, None)
            awaiting_entry.discard(message.from_user.id)
            pending_mutation.pop(message.from_user.id, None)
            await message.answer("Cancelled.")
            return
        if message.text.strip().lower() in {"/confirm", "confirm"}:
            mutation = pending_mutation.pop(message.from_user.id, None)
            if mutation:
                try:
                    if mutation[0] == "delete": await delete_entry(mutation[1])
                    elif mutation[0] == "profile": await update_profile(mutation[2] or {})
                    elif mutation[0] == "manage":
                        resource, action = mutation[1].split(":", 1)
                        await manage_content(resource, action, mutation[2] or {})
                    else: await update_entry(mutation[1], mutation[2] or {})
                    await message.answer("Profile updated." if mutation[0] == "profile" else "Content managed." if mutation[0] == "manage" else "Entry updated." if mutation[0] == "edit" else "Entry deleted.")
                except Exception:
                    await message.answer("The backend rejected that change.")
                return
            entry = pending.pop(message.from_user.id, None)
            if not entry:
                await message.answer("There is no pending preview.")
                return
            try:
                created = await create_entry(entry)
                await message.answer(f"Saved entry: {html.escape(created['title'], quote=False)}")
            except Exception:
                pending[message.from_user.id] = entry
                await message.answer("The backend rejected the entry. The preview is still pending.")
            return
        if message.from_user.id in awaiting_entry:
            try:
                entry = await extract_entry(message.text)
                pending[message.from_user.id] = entry
                awaiting_entry.discard(message.from_user.id)
                await message.answer("Preview (send /confirm to save, /cancel to discard):\n\n" + format_preview(entry))
            except Exception:
                await message.answer("I couldn't extract a valid entry. Please provide a clearer instruction.")
            return
    try:
        response = await answer(message.text or "")
    except Exception:
        logger.exception("Public portfolio lookup failed")
        response = "I couldn't reach the portfolio right now. Please try again shortly."
    await message.answer(telegram_html(response))


@dispatcher.message(lambda message: bool(message.document))
async def document(message: types.Message):
    if not is_admin(message):
        await message.answer("Document ingestion is restricted to the administrator.")
        return
    try:
        asset_request = pending_upload.pop(message.from_user.id, None)
        telegram_file = await bot.get_file(message.document.file_id)
        buffer = __import__('io').BytesIO()
        await bot.download_file(telegram_file.file_path, buffer)
        filename = message.document.file_name or "upload"
        if asset_request:
            asset_type, label = asset_request
            result = await upload_asset(asset_type, label, filename, buffer.getvalue(), message.document.mime_type)
            await message.answer(f"Asset uploaded: {html.escape(result['label'], quote=False)}")
        else:
            result = await upload_certificate(message.caption or filename, filename, buffer.getvalue(), message.document.mime_type)
            await message.answer(f"Certificate uploaded: {html.escape(result['title'], quote=False)}")
    except Exception:
        logger.exception("Certificate upload failed")
        await message.answer("I couldn't upload that certificate. Please check R2 configuration and try again.")


def format_preview(entry: dict) -> str:
    fields = ("title", "content_type", "blurb", "date", "year", "tech_stack", "tags", "links")
    return "\n".join(f"{field}: {html.escape(str(entry.get(field) or '—'), quote=False)}" for field in fields)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/telegram/webhook")
async def webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    await dispatcher.feed_update(bot, types.Update.model_validate(await request.json(), context={"bot": bot}))
    return {"ok": True}
