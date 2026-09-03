from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from fastapi import FastAPI, Header, HTTPException, Request

from .config import settings
from .llm import answer
from .llm import extract_entry
from .admin import create_entry

bot = Bot(settings.telegram_bot_token)
dispatcher = Dispatcher()
app = FastAPI(title="mikesplore Telegram bot")
pending: dict[int, dict] = {}


def is_admin(message: types.Message) -> bool:
    return bool(message.from_user and message.from_user.id == settings.admin_telegram_id)


@dispatcher.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Ask me about Michael's projects, writing, hackathons, or events.")


@dispatcher.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer("Use /start, /help, or ask a question about the public portfolio.")


@dispatcher.message()
async def question(message: types.Message):
    if is_admin(message) and message.text:
        if message.text.strip().lower() in {"/cancel", "cancel"}:
            pending.pop(message.from_user.id, None)
            await message.answer("Cancelled.")
            return
        if message.text.strip().lower() in {"/confirm", "confirm"}:
            entry = pending.pop(message.from_user.id, None)
            if not entry:
                await message.answer("There is no pending preview.")
                return
            try:
                created = await create_entry(entry)
                await message.answer(f"Saved entry: {created['title']}")
            except Exception:
                pending[message.from_user.id] = entry
                await message.answer("The backend rejected the entry. The preview is still pending.")
            return
        try:
            entry = await extract_entry(message.text)
            pending[message.from_user.id] = entry
            await message.answer("Preview (send /confirm to save, /cancel to discard):\n\n" + format_preview(entry))
        except Exception:
            await message.answer("I couldn't extract a valid entry. Please provide a clearer instruction.")
        return
    await message.answer(await answer(message.text or ""))


@dispatcher.message(lambda message: bool(message.document))
async def document(message: types.Message):
    if not is_admin(message):
        await message.answer("Document ingestion is restricted to the administrator.")
        return
    await message.answer("Documents are not yet supported. Send the entry instruction as text.")


def format_preview(entry: dict) -> str:
    fields = ("title", "content_type", "blurb", "date", "year", "tech_stack", "tags", "links")
    return "\n".join(f"{field}: {entry.get(field) or '—'}" for field in fields)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/telegram/webhook")
async def webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    await dispatcher.feed_update(bot, types.Update.model_validate(await request.json(), context={"bot": bot}))
    return {"ok": True}
