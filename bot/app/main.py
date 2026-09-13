from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from fastapi import FastAPI, Header, HTTPException, Request
import html
import httpx
import logging
import json
import re
import asyncio
import time
from contextlib import asynccontextmanager
from .tools import list_certificates

from .config import settings
from .llm import answer
from .llm import extract_entry, extract_job_description_from_image, extract_update, friendly_error, present_admin_result, tailor_cv
from .admin import apply_sync, bulk_manage_links, create_entry, delete_asset, delete_certificate, delete_entry, get_cv_base, get_profile, list_admin_resource, list_certificates as list_certificate_records, manage_content, preview_sync, render_cv, save_cv_base, update_entry, update_profile, upload_asset, upload_certificate
from .formatting import telegram_html
from .state import admin_result_context, awaiting_cv, awaiting_entry, conversation_history, last_cv_delivery, list_context, pending, pending_cv, pending_mutation, pending_sync, pending_upload, pending_upload_target, wizard_sessions
from .admin_operations import execute_admin_operation as run_admin_operation
from .callbacks import acknowledge, is_protected_action
from . import browse
from . import wizard
from .callback_handlers import register_callbacks
from .uploads import register_upload_handler
from .message_handlers import register_message_handlers
from .admin_handlers import configure as configure_admin_handlers, handle_llm_admin_operation
from .cv_handlers import configure as configure_cv_handlers, deliver_certificates, format_cv_patch, prepare_cv_patch, send_cv

bot = Bot(settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dispatcher = Dispatcher()
# Telegram retries a webhook update when the original HTTP response is delayed
# or lost. Keep a short-lived update-id cache so a retry cannot trigger a second
# LLM request or duplicate Telegram response.
processed_update_ids: dict[int, float] = {}
update_id_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await register_commands()
    yield


app = FastAPI(title="Portfolio Telegram bot", lifespan=lifespan)
logger = logging.getLogger(__name__)
async def show_typing(message: types.Message) -> None:
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")


async def register_commands():
    """Publish Telegram's command menu when the webhook process starts."""
    await bot.set_my_short_description(
        "Browse the portfolio with buttons or ask about projects, skills, and certifications."
    )
    await bot.set_my_description(
        "This is a portfolio assistant. Browse projects, writing, hackathons, skills, "
        "certificates, and contact links with the /menu buttons, or ask about the owner's "
        "background and experience. Button views read live portfolio data directly; "
        "questions are answered with AI grounded in the current portfolio data."
    )
    public_commands = [
        types.BotCommand(command="start", description="Welcome and portfolio menu"),
        types.BotCommand(command="menu", description="Browse the portfolio with buttons"),
        types.BotCommand(command="help", description="How to use this bot"),
    ]
    admin_commands = public_commands + [
        types.BotCommand(command="manage", description="Edit portfolio content with buttons"),
        types.BotCommand(command="cancel", description="Cancel a pending change"),
        types.BotCommand(command="apply", description="Recheck and apply a pending CV proposal"),
    ]
    await bot.set_my_commands(public_commands)
    await bot.set_my_commands(
        admin_commands,
        scope=types.BotCommandScopeChat(chat_id=settings.admin_telegram_id),
    )


def is_admin(message: types.Message) -> bool:
    return bool(message.from_user and message.from_user.id == settings.admin_telegram_id)


HELP_TEXT = (
    "🧭 <b>How to use this bot</b>\n"
    "\n"
    "• /menu — browse the portfolio with buttons: projects, articles, hackathons, events, "
    "skills, certificates, contact links, and more. Button views read the live portfolio data "
    "directly, so they are instant and never hit AI rate limits.\n"
    "• Free text — just ask anything. Questions are answered by AI grounded in the live "
    "portfolio data.\n"
    "• /cancel — cancel a pending change (portfolio owner only).\n"
    "• /apply — recheck and apply a pending CV proposal after the base CV changes.\n"
    "\n"
    "<b>Portfolio owner</b>\n"
    "• /manage — edit profile, projects, links, skills, education, bucket list or "
    "certificates step by step with buttons, and upload new files.\n"
    "• /manage &lt;resource&gt; — jump straight to a resource (e.g. /manage profile, "
    "/manage projects, /manage projects new)."
)


@dispatcher.message(Command("start"))
async def start(message: types.Message):
    # Fully deterministic: /start renders counts and the browse keyboard directly
    # from backend reads instead of spending LLM tokens on a greeting.
    first_name = message.from_user.first_name if message.from_user else None
    await browse.send_menu(message, first_name)


@dispatcher.message(Command("menu"))
async def menu(message: types.Message):
    first_name = message.from_user.first_name if message.from_user else None
    await browse.send_menu(message, first_name)


@dispatcher.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        HELP_TEXT,
        reply_markup=browse.menu_keyboard(),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@dispatcher.message(Command("apply"))
async def apply_command(message: types.Message):
    """Reconcile a pending CV proposal with the current base CV.

    Rendering is protected by a base revision check. If the base CV changed
    while the proposal was waiting for approval, regenerate the proposal
    against the current base so the owner can review it again.
    """
    if not is_admin(message):
        await message.answer("This command is restricted to the portfolio owner.")
        return
    tailored = pending_cv.get(message.from_user.id)
    if not tailored:
        await message.answer("There is no pending CV proposal to apply.")
        return
    _patch, job_description, _label, _revision = tailored
    await prepare_cv_patch(
        message,
        job_description,
        "The base CV changed while this proposal was pending. Rebuild the proposal using the current base CV and show the updated proposed changes for approval.",
    )


@dispatcher.message(Command("manage"))
async def manage_command(message: types.Message):
    if not is_admin(message):
        await message.answer("This command is restricted to the portfolio owner.")
        return
    await wizard.handle_manage_command(message)



def format_preview(entry: dict) -> str:
    if "resource" in entry and "action" in entry and "payload" in entry:
        return "\n".join([
            f"Resource: {html.escape(str(entry.get('resource')), quote=False)}",
            f"Action: {html.escape(str(entry.get('action')), quote=False)}",
            f"Record ID: {html.escape(str(entry.get('id') or 'new record'), quote=False)}",
            *( ["Target:", html.escape(json.dumps(entry.get("target"), indent=2, default=str), quote=False)] if entry.get("target") else [] ),
            "Changes:",
            html.escape(str(entry.get("payload") or "—"), quote=False),
        ])
    if "candidates" in entry:
        return "\n".join(f"{candidate.get('resource')}: {candidate.get('record')}" for candidate in entry["candidates"])
    fields = ("resource", "action", "id", "title", "content_type", "blurb", "date", "year", "tech_stack", "tags", "links", "payload", "candidates")
    return "\n".join(f"{field}: {html.escape(str(entry.get(field) or '—'), quote=False)}" for field in fields)


def format_profile_preview(changes: dict) -> str:
    fields = ("name", "tagline", "location", "focus", "experience", "availability_status", "availability_detail", "about")
    return "\n".join(f"{field}: {html.escape(str(changes.get(field) or '—'), quote=False)}" for field in fields if field in changes)


def format_admin_list(resource: str, items: list[dict]) -> str:
    lines = [f"{html.escape(resource.title(), quote=False)} ({len(items)})", ""]
    for index, item in enumerate(items, 1):
        if resource == "assets":
            lines += [f"{index}. {html.escape(str(item.get('label') or item.get('asset_type') or 'Unnamed asset'), quote=False)}", f"   Asset ID: {item.get('id', '—')}", f"   Type: {html.escape(str(item.get('asset_type') or '—'), quote=False)}", f"   URL: {html.escape(str(item.get('url') or '—'), quote=False)}", ""]
        elif resource == "entry-assets":
            lines += [f"{index}. {html.escape(str(item.get('alt_text') or item.get('caption') or 'Unnamed asset'), quote=False)}", f"   Entry ID: {item.get('entry_id', '—')}", f"   Asset ID: {item.get('asset_id', '—')}", f"   Role: {html.escape(str(item.get('role') or '—'), quote=False)}", f"   Caption: {html.escape(str(item.get('caption') or '—'), quote=False)}", f"   Order: {item.get('custom_order', 0)}", ""]
        elif resource == "links":
            lines += [f"{index}. {html.escape(str(item.get('name') or item.get('label') or 'Unnamed link'), quote=False)}", f"   URL: {html.escape(str(item.get('url') or '—'), quote=False)}", f"   Category: {html.escape(str(item.get('category') or '—'), quote=False)}", f"   Handle: {html.escape(str(item.get('handle') or '—'), quote=False)}", ""]
        else:
            title = item.get("title") or item.get("name") or item.get("label") or item.get("id") or "Record"
            lines.append(f"{index}. {html.escape(str(title), quote=False)} ({html.escape(str(item.get('id') or '—'), quote=False)})")
    return "\n".join(lines)[:3900]


def cv_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", str(name).strip()).strip("_")
    return f"{cleaned or 'CV'}.pdf"


register_callbacks(dispatcher, {
    "settings": settings,
    "is_protected_action": is_protected_action,
    "acknowledge": acknowledge,
    "logger": logger,
    "pending_mutation": pending_mutation,
    "pending_upload": pending_upload,
    "pending_upload_target": pending_upload_target,
    "pending_cv": pending_cv,
    "last_cv_delivery": last_cv_delivery,
    "admin_result_context": admin_result_context,
    "run_admin_operation": run_admin_operation,
    "update_profile": update_profile,
    "manage_content": manage_content,
    "bulk_manage_links": bulk_manage_links,
    "render_cv": render_cv,
    "cv_filename": cv_filename,
    "present_admin_result": present_admin_result,
    "telegram_html": telegram_html,
    "httpx": httpx,
    "types": types,
    "InlineKeyboardButton": InlineKeyboardButton,
    "InlineKeyboardMarkup": InlineKeyboardMarkup,
    "wizard": wizard,
})


register_upload_handler(dispatcher, {
    "is_admin": is_admin,
    "awaiting_cv": awaiting_cv,
    "pending_upload": pending_upload,
    "pending_upload_target": pending_upload_target,
    "show_typing": show_typing,
    "bot": bot,
    "extract_job_description_from_image": extract_job_description_from_image,
    "prepare_cv_patch": prepare_cv_patch,
    "save_cv_base": save_cv_base,
    "upload_certificate": upload_certificate,
    "upload_asset": upload_asset,
    "manage_content": manage_content,
    "logger": logger,
    "html": html,
    "httpx": httpx,
    "types": types,
    "InlineKeyboardButton": InlineKeyboardButton,
    "InlineKeyboardMarkup": InlineKeyboardMarkup,
    "wizard": wizard,
    "wizard_sessions": wizard_sessions,
})


configure_cv_handlers({
    "pending_cv": pending_cv,
    "tailor_cv": tailor_cv,
    "get_cv_base": get_cv_base,
    "format_cv_patch": format_cv_patch,
    "logger": logger,
    "html": html,
    "InlineKeyboardButton": InlineKeyboardButton,
    "InlineKeyboardMarkup": InlineKeyboardMarkup,
    "list_certificates": list_certificates,
    "httpx": httpx,
    "types": types,
    "settings": settings,
    "friendly_error": friendly_error,
})


register_message_handlers(dispatcher, {
    "is_admin": is_admin,
    "pending": pending,
    "awaiting_entry": awaiting_entry,
    "pending_mutation": pending_mutation,
    "pending_upload_target": pending_upload_target,
    "pending_sync": pending_sync,
    "awaiting_cv": awaiting_cv,
    "pending_cv": pending_cv,
    "conversation_history": conversation_history,
    "list_context": list_context,
    "tailor_cv": tailor_cv,
    "apply_sync": apply_sync,
    "render_cv": render_cv,
    "send_cv": send_cv,
    "deliver_certificates": deliver_certificates,
    "last_cv_delivery": last_cv_delivery,
    "create_entry": create_entry,
    "delete_entry": delete_entry,
    "delete_asset": delete_asset,
    "delete_certificate": delete_certificate,
    "update_profile": update_profile,
    "manage_content": manage_content,
    "run_admin_operation": run_admin_operation,
    "bulk_manage_links": bulk_manage_links,
    "update_entry": update_entry,
    "show_typing": show_typing,
    "extract_entry": extract_entry,
    "answer": answer,
    "handle_llm_admin_operation": handle_llm_admin_operation,
    "telegram_html": telegram_html,
    "cv_filename": cv_filename,
    "format_preview": format_preview,
    "format_cv_patch": format_cv_patch,
    "logger": logger,
    "html": html,
    "httpx": httpx,
    "json": json,
    "asyncio": asyncio,
    "types": types,
    "InlineKeyboardButton": InlineKeyboardButton,
    "InlineKeyboardMarkup": InlineKeyboardMarkup,
    "friendly_error": friendly_error,
    "wizard": wizard,
    "wizard_sessions": wizard_sessions,
    "handle_wizard_text": wizard.handle_wizard_text,
    "handle_wizard_sub_text": wizard.handle_wizard_sub_text,
})


configure_admin_handlers({
    "pending_upload": pending_upload,
    "pending_upload_target": pending_upload_target,
    "pending_mutation": pending_mutation,
    "pending_cv": pending_cv,
    "manage_content": manage_content,
    "present_admin_result": present_admin_result,
    "telegram_html": telegram_html,
    "run_admin_operation": run_admin_operation,
    "update_profile": update_profile,
    "bulk_manage_links": bulk_manage_links,
    "prepare_cv_patch": prepare_cv_patch,
    "logger": logger,
    "InlineKeyboardButton": InlineKeyboardButton,
    "InlineKeyboardMarkup": InlineKeyboardMarkup,
})

wizard.configure({
    "wizard_sessions": wizard_sessions,
    "pending_upload": pending_upload,
    "pending_upload_target": pending_upload_target,
    "update_profile": update_profile,
    "manage_content": manage_content,
    "bulk_manage_links": bulk_manage_links,
    "list_admin_resource": list_admin_resource,
    "get_profile": get_profile,
    "is_admin": is_admin,
})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/telegram/webhook")
async def webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    now = time.monotonic()
    async with update_id_lock:
        # Keep five minutes of IDs; Telegram's retry window is much shorter,
        # while this bound prevents an unbounded in-memory structure.
        for update_id, seen_at in list(processed_update_ids.items()):
            if now - seen_at > 300:
                processed_update_ids.pop(update_id, None)
        if update.update_id in processed_update_ids:
            return {"ok": True, "duplicate": True}
        processed_update_ids[update.update_id] = now
    await dispatcher.feed_update(bot, update)
    return {"ok": True}
