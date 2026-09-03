# Deployment checklist

The database schema is managed by Alembic. A deployment connected to the already-populated
production database does not need to run seed scripts. Run migrations only when a new migration
file is introduced, and only after verifying `DATABASE_URL` points to the intended database.

## Services

Run the backend from `backend/`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Run the bot from `bot/`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

The reverse proxy must expose the bot at `/telegram/webhook` and forward the
`X-Telegram-Bot-Api-Secret-Token` header. Configure Telegram with the public HTTPS webhook URL.

## Environment

Copy `.env.example` to the repository root and set the real values. Required values include the
database URL, service API key, Telegram token and webhook secret, Groq key, and R2 credentials.
Never commit `.env`.

## Verification

```bash
curl https://api.example.com/health
curl https://bot.example.com/health
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo"
```

Confirm the frontend `VITE_API_BASE_URL` points to the public backend URL, R2 public URLs open,
and PostgreSQL backups/persistent storage are enabled on the hosting platform.
