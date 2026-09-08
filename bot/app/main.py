from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
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
from .tools import list_certificates

from .config import settings
from .llm import answer
from .llm import extract_entry, extract_job_description_from_image, extract_update, present_admin_result, request_cv_render, tailor_cv
from .admin import apply_sync, bulk_manage_links, create_entry, delete_asset, delete_certificate, delete_entry, get_cv_base, list_certificates as list_certificate_records, manage_content, preview_sync, render_cv, save_cv_base, update_entry, update_profile, upload_asset, upload_certificate
from .formatting import telegram_html
from .state import admin_result_context, awaiting_cv, awaiting_entry, conversation_history, last_cv_delivery, list_context, pending, pending_cv, pending_mutation, pending_sync, pending_upload, pending_upload_target
from .admin_operations import execute_admin_operation as run_admin_operation
from .callbacks import acknowledge, is_protected_action
from .callback_handlers import register_callbacks
from .uploads import register_upload_handler
from .message_handlers import register_message_handlers
from .admin_handlers import configure as configure_admin_handlers, handle_llm_admin_operation
from .cv_handlers import configure as configure_cv_handlers, deliver_certificates, format_cv_patch, prepare_cv_patch, send_cv

bot = Bot(settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dispatcher = Dispatcher()
app = FastAPI(title="Portfolio Telegram bot")
logger = logging.getLogger(__name__)
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
    ]
    admin_commands = public_commands + [
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
    first_name = message.from_user.first_name if message.from_user else None
    last_name = message.from_user.last_name if message.from_user else None
    response = await answer(
        "Create a concise first-contact welcome using only current tool results. Look up the verified profile and available public portfolio collections first. Address the sender by their Telegram first name when available, identify the portfolio owner using the verified profile, and describe only the content categories that actually exist in the returned data. Do not use a hardcoded greeting, topic list, tagline, location, or portfolio fact.",
        user_context={"first_name": first_name, "last_name": last_name, "is_admin": is_admin(message)},
    )
    await message.answer(telegram_html(response))


async def _removed_admin_handler_placeholder(message: types.Message, operation: dict) -> bool:
    """Handle an operation returned by the single main LLM orchestration loop."""
    user_id = message.from_user.id
    resource, action = operation.get("resource"), operation.get("action")
    if resource == "uploads" and action == "request":
        upload = operation.get("payload") or {}
        asset_type = upload.get("asset_type")
        if not asset_type:
            await message.answer("The upload request did not specify an asset type.")
            return True
        pending_upload[user_id] = (asset_type, upload.get("label") or asset_type)
        if upload.get("entry_id"):
            pending_upload_target[user_id] = {"entry_id": upload["entry_id"], "role": upload.get("role", "gallery")}
        await message.answer(f"Please attach the {asset_type} file.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Cancel upload", callback_data="upload:cancel")]]))
        return True
    if resource == "cv-tailoring" and action == "request":
        job_description = (operation.get("payload") or {}).get("job_description", "").strip()
        if len(job_description) < 30:
            await message.answer("The job description is too short to tailor the CV.")
        else:
            await prepare_cv_patch(message, job_description)
        return True
    if resource == "role-policies" and action == "propose":
        policies = (operation.get("payload") or {}).get("policies") or []
        for policy in policies:
            await manage_content("role-policies", "create", policy)
        names = ", ".join(policy.get("role_family", "").title() for policy in policies)
        await message.answer(f"Saved {len(policies)} pending role polic{'y' if len(policies) == 1 else 'ies'}: {names}." if policies else "I found no evidence-supported role policies.")
        return True
    if resource == "devto-sync" and action == "request":
        result = operation.get("payload") or {}
        await message.answer(f"Synced {result.get('updated', 0)} Dev.to article(s), including their public bodies.")
        return True
    if not resource or not action:
        return False
    if action == "list":
        items = await manage_content(resource, "list", {})
        response = await present_admin_result(message.text or "", resource, items[:5], {"is_admin": True})
        await message.answer(telegram_html(response))
        return True
    if action == "delete":
        if operation.get("id"):
            records = await manage_content(resource, "list", {})
            operation["target"] = next((item for item in records if str(item.get("id")) == str(operation["id"])), None)
        pending_mutation[user_id] = ("admin", f"{resource}:{action}", operation)
        target = operation.get("target") or {}
        label = target.get("name") or target.get("title") or target.get("label") or operation.get("id")
        await message.answer(f"Delete {label}?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Delete", callback_data="admin:confirm"), InlineKeyboardButton(text="Cancel", callback_data="admin:cancel")]]))
        return True
    await run_admin_operation(operation, update_profile=update_profile, manage_content=manage_content, bulk_manage_links=bulk_manage_links)
    await message.answer(f"{resource.replace('-', ' ').title()} {'updated' if action == 'update' else 'created' }.")
    return True


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
    "request_cv_render": request_cv_render,
    "render_cv": render_cv,
    "cv_filename": cv_filename,
    "present_admin_result": present_admin_result,
    "telegram_html": telegram_html,
    "httpx": httpx,
    "types": types,
    "InlineKeyboardButton": InlineKeyboardButton,
    "InlineKeyboardMarkup": InlineKeyboardMarkup,
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
    "request_cv_render": request_cv_render,
    "render_cv": render_cv,
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
    "request_cv_render": request_cv_render,
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


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/telegram/webhook")
async def webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    await dispatcher.feed_update(bot, types.Update.model_validate(await request.json(), context={"bot": bot}))
    return {"ok": True}
