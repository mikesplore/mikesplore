from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
# Local development may use the repository .env. Hosted platforms inject these
# values directly into the process environment and normally have no .env file.
# Never overwrite an already-injected value with a local dotenv value.
if ENV_FILE.is_file():
    load_dotenv(ENV_FILE, override=False)


def normalize_database_url(url: str) -> str:
    """Use the installed psycopg (v3) driver for generic Postgres URLs."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


class Settings(BaseSettings):
    database_url: str
    service_api_key: str
    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    r2_public_base_url: str = ""
    frontend_origin: str = "http://localhost:5173"
    devto_username: str = "mikesplore"
    github_username: str = "mikesplore"
    github_token: str = ""
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


settings = Settings()
settings.database_url = normalize_database_url(settings.database_url)
