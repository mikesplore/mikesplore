from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from pathlib import Path
import os

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
# Render and other hosted platforms provide configuration as environment
# variables, so a repository .env is optional. Preserve injected values.
if ENV_FILE.is_file():
    load_dotenv(ENV_FILE, override=False)


class Settings(BaseSettings):
    backend_url: str = ""
    assemblyai_api_key: str = ""
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


settings = Settings()
if not settings.backend_url:
    settings.backend_url = f"http://127.0.0.1:{os.getenv('PORT', '8000')}"
