from logging.config import fileConfig
import os
from pathlib import Path
from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
if not ENV_FILE.is_file():
    raise RuntimeError(f".env not found at expected path: {ENV_FILE}")
if not load_dotenv(ENV_FILE, override=True):
    raise RuntimeError(f"Unable to load .env at expected path: {ENV_FILE}")
if not os.getenv("DATABASE_URL"):
    raise RuntimeError(f"DATABASE_URL is missing from .env at: {ENV_FILE}")

target_metadata = None

def database_url():
    return os.environ["DATABASE_URL"]

def run_migrations_offline():
    context.configure(url=database_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
