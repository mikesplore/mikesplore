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
from .cv_handlers import configure as configure_cv_handlers, prepare_cv_patch as prepare_cv_patch_handler

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


async def prepare_cv_patch(message: types.Message, job_description: str, revision: str | None = None):
    return await prepare_cv_patch_handler(message, job_description, revision)

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


async def handle_llm_admin_operation(message: types.Message, operation: dict) -> bool:
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
        if message.text.strip().lower() == "/cancel":
            pending.pop(message.from_user.id, None)
            awaiting_entry.discard(message.from_user.id)
            pending_mutation.pop(message.from_user.id, None)
            pending_upload_target.pop(message.from_user.id, None)
            pending_sync.pop(message.from_user.id, None)
            awaiting_cv.discard(message.from_user.id)
            pending_cv.pop(message.from_user.id, None)
            await message.answer("Cancelled.")
            return
        if message.text.strip().startswith("/"):
            await message.answer("Only /start and /cancel are available. Please describe what you need in ordinary language.")
            return
        normalized_admin_text = message.text.strip().lower()
        confirmation_text = normalized_admin_text in {"yes", "confirm", "go ahead", "proceed", "do it"}
        if message.from_user.id in pending_cv and not confirmation_text:
            try:
                current_patch, job_description, label, base_revision = pending_cv[message.from_user.id]
                decision = await tailor_cv(job_description, current_patch, message.text)
                if decision.get("action") == "confirm":
                    confirmation_text = True
                elif decision.get("status") == "rejected":
                    await message.answer("I won't apply this CV revision: " + html.escape(decision.get("reason", "There is not enough verified evidence.")))
                    return
                else:
                    pending_cv[message.from_user.id] = (decision, job_description, label, base_revision)
                    await message.answer("Updated proposed CV changes:\n\n" + format_cv_patch(decision) + "\n\nConfirm, or tell me what to change.")
                    return
            except Exception:
                logger.exception("CV revision handling failed")
                await message.answer("I couldn't understand that CV change. Please describe what you want changed.")
                return
        if confirmation_text:
            sync = pending_sync.pop(message.from_user.id, None)
            if sync:
                try:
                    result = await apply_sync(sync[0], sync[1], sync[2])
                    await message.answer(f"{sync[0].title()} sync complete: {result['updated']} entries upserted.")
                except httpx.HTTPStatusError as error:
                    pending_sync[message.from_user.id] = sync
                    logger.exception("Sync apply failed with backend response")
                    await message.answer(f"The sync was rejected by the backend: {error.response.text[:800]}\n\nThe preview is still pending; fix the issue and try /confirm again.")
                except Exception:
                    pending_sync[message.from_user.id] = sync
                    logger.exception("Sync apply failed")
                    await message.answer("The sync could not be completed. The preview is still pending; try /confirm again.")
                return
            tailored = pending_cv.pop(message.from_user.id, None)
            if tailored:
                await message.answer("Confirmed. I’m now rendering the tailored PDF…")
                try:
                    patch, job_description, label, base_revision = tailored
                    render_args = await request_cv_render(patch, job_description, base_revision, label)
                    result = await render_cv(**render_args)
                    async with httpx.AsyncClient(timeout=30) as client:
                        pdf_response = await client.get(result["pdf_url"])
                        pdf_response.raise_for_status()
                    last_cv_delivery[message.from_user.id] = (result["pdf_url"], label)
                    await message.answer_document(types.BufferedInputFile(pdf_response.content, filename=cv_filename(label)), caption="Tailored CV", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="Download again", callback_data="cv:download-again"),
                    ]]))
                except httpx.HTTPStatusError as error:
                    pending_cv[message.from_user.id] = tailored
                    logger.exception("Tailored CV rejected by backend")
                    await message.answer(f"The backend rejected the tailored CV: {error.response.text[:500]}")
                except Exception as error:
                    pending_cv[message.from_user.id] = tailored
                    logger.exception("Tailored CV rendering failed")
                    await message.answer(f"The tailored CV could not be rendered: {str(error)[:500]}. The proposal is still pending; please say yes to retry or describe a change.")
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
                        result_message = await run_admin_operation(operation, update_profile=update_profile, manage_content=manage_content, bulk_manage_links=bulk_manage_links)
                    else: await update_entry(mutation[1], mutation[2] or {})
                    if mutation[0] == "profile":
                        result_message = "Profile updated."
                    elif mutation[0] == "manage":
                        result_message = "Content managed."
                    elif mutation[0] == "edit":
                        result_message = "Entry updated."
                    elif mutation[0] == "admin":
                        action = (mutation[2] or {}).get("action")
                        resource = (mutation[2] or {}).get("resource", "content")
                        result_message = {"create": f"{resource.title()} created.", "update": f"{resource.title()} updated.", "delete": f"{resource.title()} deleted."}.get(action, "Change applied.")
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
                    await message.answer("The change could not be completed. The proposal is still pending; please try again or say cancel.")
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
        question_text = message.text or ""
        user_id = message.from_user.id
        normalized = question_text.lower().strip()
        is_next = normalized in {"yes", "y", "next", "next page", "show more", "more"} or "next page" in normalized
        if is_next and user_id in list_context:
            content_type, current_page = list_context[user_id]
            question_text = f"Show page {current_page + 1} of {content_type}s from the portfolio."
            list_context[user_id] = (content_type, current_page + 1)
        elif is_next and conversation_history.get(user_id):
            # A detail follow-up such as "next" should stay with the previous
            # subject instead of becoming a fresh search for the literal word.
            question_text = "Continue with the same subject as my previous request and provide the next useful detail."
        else:
            content_type = next((value for value in ("project", "article", "hackathon", "event") if value in normalized), None)
            if content_type and any(word in normalized for word in ("show", "list", "what", "which")):
                list_context[user_id] = (content_type, 1)
        history = conversation_history.setdefault(user_id, [])
        streamed_message = await message.answer("…")
        last_edit = 0.0

        async def update_stream(text: str):
            nonlocal last_edit
            now = asyncio.get_running_loop().time()
            if now - last_edit < 0.7 and len(text) < 3900:
                return
            last_edit = now
            await streamed_message.edit_text(html.escape(text[-4000:]))

        response = await answer(
            question_text,
            history[-6:],
            on_text=update_stream,
            user_context={
                "first_name": message.from_user.first_name if message.from_user else None,
                "last_name": message.from_user.last_name if message.from_user else None,
                "is_admin": is_admin(message),
            },
        )
        if response.startswith("__ADMIN_OPERATION__"):
            await streamed_message.delete()
            operation = json.loads(response.removeprefix("__ADMIN_OPERATION__"))
            await handle_llm_admin_operation(message, operation)
            return
        history.extend([
            {"role": "user", "content": question_text},
            {"role": "assistant", "content": response},
        ])
        del history[:-6]
    if response.startswith("__BOT_ACTION__"):
        await streamed_message.delete()
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
    await streamed_message.edit_text(telegram_html(response))



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
