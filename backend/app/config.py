from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
if not ENV_FILE.is_file():
    raise RuntimeError(f".env not found at expected path: {ENV_FILE}")
if not load_dotenv(ENV_FILE, override=True):
    raise RuntimeError(f"Unable to load .env at expected path: {ENV_FILE}")


class Settings(BaseSettings):
    database_url: str
    service_api_key: str
    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    r2_public_base_url: str = ""
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


settings = Settings()
