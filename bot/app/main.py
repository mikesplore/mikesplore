from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from fastapi import FastAPI, Header, HTTPException, Request

from .config import settings
from .llm import answer

bot = Bot(settings.telegram_bot_token)
dispatcher = Dispatcher()
app = FastAPI(title="mikesplore Telegram bot")


@dispatcher.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Ask me about Michael's projects, writing, hackathons, or events.")


@dispatcher.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer("Use /start, /help, or ask a question about the public portfolio.")


@dispatcher.message()
async def question(message: types.Message):
    await message.answer(await answer(message.text or ""))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/telegram/webhook")
async def webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    await dispatcher.feed_update(bot, types.Update.model_validate(await request.json(), context={"bot": bot}))
    return {"ok": True}
