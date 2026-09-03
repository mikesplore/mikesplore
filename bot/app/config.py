from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str
    telegram_webhook_secret: str
    groq_api_key: str
    backend_url: str = "http://localhost:8000"
    groq_model: str = "llama-3.1-8b-instant"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
