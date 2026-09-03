from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseSettings):
    telegram_bot_token: str
    telegram_webhook_secret: str
    groq_api_key: str
    backend_url: str = "http://localhost:8000"
    groq_model: str = "llama-3.1-8b-instant"
    admin_telegram_id: int
    service_api_key: str
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
