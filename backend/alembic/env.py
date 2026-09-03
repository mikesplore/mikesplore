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
# A local .env is convenient for development, but deployment environments
# supply DATABASE_URL directly. Do not overwrite deployment environment vars.
if ENV_FILE.is_file():
    load_dotenv(ENV_FILE, override=False)
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL environment variable is required")

target_metadata = None

def database_url():
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url

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
