# Deployment and migration verification

Run these checks in a virtual environment with the repository dependencies installed.

## Database migration

1. Back up the production database before applying the destructive cutover.
2. Confirm the current revision:

   ```bash
   alembic current
   ```

3. Apply the complete chain:

   ```bash
   alembic upgrade head
   ```

4. Confirm the head revision:

   ```bash
   alembic current
   ```

5. Verify that `entries`, `technologies`, `repositories`, content-block tables,
   `relationships`, `admin_operations`, `admin_audit_log`, and normalized `profile_links`
   columns exist.

The historical project source is available in Git commit `4d8d521^` if a data recovery/import
operation is required.

## Backend checks

```bash
python -m compileall -q backend/app bot/app
pytest -q backend/tests
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Verify `/health`, public entries, projects, technologies, content blocks, profile links, and
protected admin endpoints with valid and invalid service keys.

## Frontend checks

```bash
cd frontend
npm ci
npm run build
```

Verify the timeline, projects, contact page, hackathons, events, and empty/error states against
the running API.

## Bot checks

Verify the following flows with the configured administrator account:

- Natural-language contact creation through `/admin`
- Contact update and delete after an LLM lookup
- Ambiguous record request is rejected for clarification
- `/confirm` applies exactly the previewed operation
- `/cancel` applies nothing
- Bulk contact creation is atomic
- Public questions use only verified API data
- File delivery and admin authorization remain functional

## Production checks

- Install the locked Python and frontend dependencies.
- Set all secrets through environment variables.
- Run migrations before starting the application.
- Confirm CORS origins and service API keys.
- Check Render logs for migration, API, bot, and database errors.
- Perform one real read and one reversible admin update after deployment.
