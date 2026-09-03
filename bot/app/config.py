from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
# Render and other hosted platforms provide configuration as environment
# variables, so a repository .env is optional. Preserve injected values.
if ENV_FILE.is_file():
    load_dotenv(ENV_FILE, override=False)


class Settings(BaseSettings):
    telegram_bot_token: str
    telegram_webhook_secret: str
    groq_api_key: str
    backend_url: str = "http://localhost:8000"
    groq_model: str = "llama-3.1-8b-instant"
    admin_telegram_id: int
    service_api_key: str
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


settings = Settings()
