# AGENTS.md — Portfolio Backend + Telegram Bot Conversion
This file tracks the phased conversion of mikesplore.me from a static, build-time-sourced
portfolio into a database-driven system served by a FastAPI backend, consumed by both the
existing frontend and a Telegram bot. Update this file as you go: log what you actually did,
any deviations from the plan below, and why. Do not silently diverge from the plan without
recording it here — this project has diverged from its plan before (multi-tab nav instead of
collapsed, always-expanded cards instead of accordion) without being written down until later,
which cost time to reconcile.

## Architecture summary

- **Repo**: single monorepo with `frontend/`, `backend/`, and `bot/` parent directories.
- **Backend**: FastAPI + PostgreSQL (SQLAlchemy + Alembic for migrations).
- **Frontend**: existing site, unchanged visually. Swaps build-time GitHub/dev.to sourcing for
  runtime calls to the backend's public REST endpoints.
- **Bot**: Telegram bot with two paths:
  - **Public read path**: any user can query it. Uses an LLM with tool-calling to query the
    backend's public REST endpoints and answer questions grounded in real data — no free
    generation of facts about Mike.
  - **Admin write path**: restricted to Mike's Telegram `user.id` only. Accepts documents or
    instructions, uses the LLM to extract structured fields, shows a preview, and on
    confirmation calls the backend's protected write endpoints.
- **LLM access is scoped to the bot only.** The backend and frontend never call an LLM directly.
- **Bot never touches the database directly.** All reads and writes go through the backend's
  REST API, same as the frontend. This keeps one source of truth for data access and validation.
- **Auth model**: Telegram `user.id` whitelist (env var `ADMIN_TELEGRAM_ID`) gates admin bot
  commands. Bot-to-backend write calls are authenticated with a separate service API key
  (env var), distinct from any end-user auth. No OTP/email step-up — it was considered and
  dropped as unnecessary for a single-admin system.
- **LLM provider**: Groq (free tier is rate-limited, not credit-limited, so it doesn't expire).
  Use the smallest/fastest model on Groq that reliably supports tool-calling — this is a
  low-complexity extraction/lookup task, not one that needs a large reasoning model. Confirm
  the current smallest tool-capable Groq model at implementation time, since model lineups
  change; do not hardcode an assumption about which one is "current" without checking.

## Phase 0 — Investigate the current static site

This phase was completed before the schema and backend work.

- Read through the existing frontend repo/codebase in full: the React components, JSDoc
  `TimelineEntry` model, and build-time content sourcing from dev.to and GitHub.
- Catalog every distinct content type currently rendered: projects, hackathon wins, articles,
  client deployments, tech stack tags, contact links, etc. Note which fields each type has
  (title, description, tech stack, links, dates, featured/priority ordering, etc.) and which
  fields are manually curated vs. pulled live from GitHub/dev.to.
- Note where the built version has already diverged from any prior plan (multi-tab nav,
  always-expanded cards) — these are current real behavior, not bugs, and the new schema/API
  needs to support them, not the originally planned version.
- Write a short "Current State" section into this file summarizing findings before moving to
  Phase 1. If the schema in Phase 1 doesn't map cleanly onto something found here, flag it here
  rather than quietly designing around it.

### Current State (Phase 0 findings — 2026-09-03)

- The Vite/React frontend now lives under `frontend/` (`frontend/src/`, `frontend/scripts/`, and
  `frontend/public/`); `backend/` and `bot/` contain the service implementations.
- The site has route-based navigation for About, Projects, Timeline, Hackathons, Certificates,
  Events, Bucket list, Contact, and CV. Navigation is a horizontally scrollable multi-tab bar
  with item counts for several curated collections. Project cards link to detail pages. Timeline
  rows are currently collapsed by default and individually expandable (the current implementation
  is accordion-like, despite the historical note about always-expanded cards).
- Timeline entries are the closest existing unified feed model. `TimelineEntry` is documented as
  `date`, `type`, `title`, `blurb`, optional `link`, and optional `tags`. The UI additionally
  consumes optional `readTime`, `stars`, and `thumbnail`. The current static snapshot contains
  38 entries: 11 articles from dev.to and 27 GitHub-derived entries (exact counts can change when
  the build-time fetch runs).
- `scripts/fetch-devto.js` calls the dev.to articles endpoint for `mikesplore` and maps manually
  selected API fields: publication date, title, description, URL, up to five tags, reading time,
  and cover/social image. `scripts/fetch-github.js` calls the GitHub repositories endpoint,
  includes only allowlisted project/hobby repositories (and selected forks), maps creation date,
  name, description, URL, primary language, star count, and owner avatar, and supports a manual
  override for selected repositories. Before Phase 3, `src/data/entries.js` merged both generated
  JSON files, deduplicated by normalized link/title, and sorted newest first.
- There is an existing type mismatch to resolve explicitly in Phase 1: `src/data/types.js`
  documents and filters `repo` and `articles`, but GitHub ingestion emits `project` and `hobby`.
  Consequently the unfiltered timeline displays GitHub entries, while the “GitHub” filter does
  not match them and its count is wrong. The new API/schema should use one intentional taxonomy
  and preserve source metadata if useful; this is not a reason to create separate tables.
- Curated projects are a separate collection of 15 records in `projectsCatalog.js`, with fields
  `id`, `title`, `tagline`, `summary`, optional `overview`/`details`, `platform`, `type`, `status`,
  `stack`, `tags`, `cardImage`, `gallery`, and `links.repo`/`links.demo`. These records overlap
  conceptually with GitHub timeline entries but are richer editorial project pages and should
  not be silently replaced by repository metadata.
- Curated hackathons are 7 records in `profile.js`: `title`, `result`, optional `project`,
  `description`, `year`, `organization`, `link`, and `image`. Events are a separate 17-record
  collection in `events.js` with `title`, `date`, `location`, `blurb`, `image`, and `link` in the
  current data (the renderer also supports optional `photos` and `id`). These represent distinct
  achievement and community/event content types.
- Other manually curated content includes: profile/status and availability text; professional
  links (GitHub, dev.to, Google Developers, Lablab, Kaggle, X, email); messaging/social links
  (Instagram, Telegram, X, WhatsApp); grouped skills; one education record; five certificate
  image records; 23 bucket-list records (`id`, `title`, `done`, `remark`); CV PDF; and long-form
  About page copy. The current pages render these directly from JS/assets, not from an API.
- Phase 1 mapping implications: a unified entries table maps well to timeline/project/hackathon/
  event records if it supports a deliberate `content_type`, visibility/featured/order controls,
  rich text fields, JSON/array metadata, links, media, and source/provenance. Certificates,
  profile/contact/settings, education, bucket-list items, and CV are not timeline entries and need
  either additive tables or a separately justified migration decision. Existing `stack` vs
  `tags`, nested links, galleries, and the distinction between article/repository metadata and
  editorial project details must be represented explicitly rather than flattened accidentally.

## Phase 1 — Database design

- Design the Postgres schema based on Phase 0 findings. Prefer a single unified entries table
  (mirroring the existing `TimelineEntry` concept) over separate tables per content type, unless
  Phase 0 turns up a strong reason not to — the frontend already treats these as one unified
  feed.
- Required fields on entries, minimum: `is_visible` (bool), `is_featured` (bool), `custom_order`
  (int), `tech_stack` (array/JSON), plus whatever content fields Phase 0 identified.
- Set up Alembic migrations from the start, not as an afterthought.
- No separate "admin" DB table is needed for auth — that's an env var. If a write-audit log is
  wanted later, design it as a strictly additive table, not a blocker for this phase.

### Phase 1 implementation log (2026-09-03)

- Added `backend/` migration foundation with SQLAlchemy/Alembic/PostgreSQL dependencies and an
  initial `0001_initial_schema` migration.
- Added unified `entries` table with constrained content types (`project`, `article`, `hackathon`,
  `event`), publication date/year, visibility, featured flag, custom ordering, array-backed
  `tech_stack`/`tags`, JSONB details/links/media/source, and timestamps. `source` preserves whether
  data came from GitHub/dev.to or was manually curated.
- Added separate tables for profile, profile links, education, certificates, bucket-list items,
  and site assets. No admin/auth table was added; authentication remains environment-based as
  specified by the plan.
- Used PostgreSQL `gen_random_uuid()` via the `pgcrypto` extension for UUID-backed records. API
  models, seed/import tooling, and endpoints remain deferred to Phase 2 and later.

## Phase 2 — Backend API (FastAPI)

- Project skeleton: FastAPI + SQLAlchemy + Alembic, Pydantic schemas matching the Phase 1 schema.
- Public endpoints (no auth): `GET` list and detail routes, filtered to `is_visible = true`,
  ordered by `custom_order`.
- Protected write endpoints (service API key required): create/update/delete on entries. These
  are the endpoints the bot's admin path calls — never called by the public frontend.
- Write basic tests for the visibility filter (a visible=false entry must never appear on a
  public endpoint) before moving on — this is the one bug that would defeat the entire point of
  curation.

### Phase 2 implementation log (2026-09-03)

- Added FastAPI application under `backend/app` with SQLAlchemy session dependency, Pydantic
  request/response schemas, and `/health`.
- Added public `GET /entries` and `GET /entries/{id}` routes. Both enforce `is_visible = true`;
  list results support an optional content-type filter and are ordered by `custom_order`, then
  date descending.
- Added service-key-protected create, patch, and delete routes using `X-Service-Api-Key`.
  Writes are rejected when the service key is unset or incorrect.
- Added a visibility regression test. The API layer is intentionally limited to entries; routes
  for profile and other collections can be added after the frontend migration requirements are
  clearer.

## Phase 3 — Frontend migration

- Replace the build-time GitHub/dev.to fetching with runtime fetch calls to the backend's public
  endpoints.
- Visual output must not change. This is a data-source swap, not a redesign.
- Remove the now-dead build-time sourcing code rather than leaving it dormant.

### Phase 3 implementation log (2026-09-03)

- Migrated the timeline from bundled `entries.devto.json`/`entries.github.json` data to runtime
  `GET /entries` calls through `src/lib/portfolioApi.js`, using `VITE_API_BASE_URL` with a local
  development default.
- Added loading and temporary-unavailable states while preserving the existing expandable row
  presentation. The adapter maps backend links/media/details JSONB into the timeline's display
  shape.
- Updated timeline taxonomy to match the backend (`project`, `article`, `hackathon`, `event`),
  fixing the Phase 0 GitHub filter mismatch.
- Removed the build-time entry fetch scripts from the npm build lifecycle. Curated project pages,
  hackathons, events, profile data, and other collections remain static because they do not yet
  have backend read endpoints.
- The fetch scripts and generated JSON files remain in the repository as historical/possible
  import material; they are no longer invoked by builds. This is a documented deviation from the
  original “remove dead sourcing code” bullet and should be resolved when the import path is settled.

### Repository structure update (2026-09-03)

- Moved all frontend application files, assets, scripts, and npm configuration into `frontend/`
  so the monorepo now matches the intended top-level structure. `AGENTS.md`, shared repository
  metadata, `backend/`, and `bot/` remain at the repository root.

- Migrated Hackathons and Events pages to fetch their entries from the backend at runtime,
  including event location, links, images, and gallery metadata.
- Migrated Header and Availability Banner to load profile and professional links from the backend;
  the profile image remains a local asset until its R2 asset record is populated.
- Migrated CV education rendering to `GET /education`; the CV PDF itself remains local pending
  R2 asset upload and frontend URL migration.
- Removed the final Header profile-image and CV-PDF frontend imports; both now resolve through
  `/assets` and require corresponding R2 asset records.
- Migrated Home/About narrative rendering to the profile API; the existing copy is now seeded in
  `profile.about` and rendered as database-provided sections.
- Added `/counts` and migrated navigation badges to runtime counts instead of static collection
  imports.

## Phase 4 — Telegram bot: public read path

- Bot skeleton with webhook-based updates (not long-polling).
- LLM tool-calling setup: define tools that call the backend's public REST endpoints. The model
  answers questions by calling these tools, not by generating facts from its own training data.
- Keep a couple of hardcoded commands (`/start`, `/help`) for basic navigation; route actual
  content questions through the LLM tool-calling path rather than building a parallel hardcoded
  command menu for each content type.

### Phase 4 implementation log (2026-09-03)

- Added a webhook-based `aiogram` bot under `bot/app`; `aiogram` was selected for its native
  async Dispatcher and webhook update handling.
- Added `/start` and `/help`, plus a public question handler that uses Groq tool calling.
- The only tool calls the backend's public `GET /entries` endpoint. The bot has no database access
  and does not use the protected write API.
- Verified against current Groq documentation: Groq states that all hosted models support tool
  use. Configured `llama-3.1-8b-instant` as the small/fast default, with `GROQ_MODEL` overridable
  through environment configuration. Recheck the active model lineup before deployment.

## Phase 5 — Telegram bot: admin write path

- Middleware: reject any write-path command where `message.from.id != ADMIN_TELEGRAM_ID`.
- Accept a document or free-text instruction from the admin, use the LLM to extract structured
  fields matching the Phase 1 schema.
- Show a preview of the extracted data and require explicit confirmation before the bot calls
  the backend's protected write endpoint. This confirm step is the actual safety net against bad
  extractions — treat it as required, not optional polish.
- No GitHub webhook auto-sync in this phase. Ingestion is document/instruction-driven only, by
  design — the point is curation, not mirroring every repo.

### Phase 5 implementation log (2026-09-03)

- Added administrator authorization using `ADMIN_TELEGRAM_ID`; non-admin users cannot enter the
  write flow.
- Added Groq JSON extraction for free-text entry instructions, an in-memory pending preview, and
  explicit `/confirm` or `/cancel` handling.
- Confirmed writes call only the backend's protected `POST /entries` endpoint with the separate
  service API key. Failed writes retain the pending preview for retry.
- Document messages are rejected with guidance to send text. Full document extraction remains
  deferred because no document parsing policy/dependency has been selected yet.
- Corrected admin message routing so public questions remain on the read path; entry extraction
  now starts only after the administrator explicitly sends `/add`.
- Added public-path API error handling: failures are logged by the bot and produce a retry message
  in Telegram instead of a silent response.
- Added public `GET /profile` and a `get_profile` LLM tool so identity and background questions use
  verified profile data. Added a profile seed command.
- Enabled Telegram HTML parsing with a formatter for the LLM's common Markdown output, so headings,
  emphasis, links, and code render reliably without MarkdownV2 escaping errors.
- Added public `/search` across visible entries and profile context, plus a compact paginated
  `search_portfolio` LLM tool for broad or ambiguous user questions.
- Added public certificate listing and direct Telegram certificate delivery. Certificate files are
  fetched by the bot and sent directly; they are not uploaded to or interpreted by the LLM.
- Began full collection migration with migration `0003`, skill/settings storage, and public API
  routes for profile links, education, skills, and settings. These endpoints precede frontend
  runtime migration; projects, events, hackathons, bucket-list, and upload-backed assets remain
  next.
- Added public `/bucket-list` and `/assets` routes with SQLAlchemy models for the remaining
  existing collections. Frontend runtime adapters and import/seed mappings for these collections
  are still pending.
- Added a reproducible frontend content exporter and curated seed command for projects, events,
  hackathons, bucket-list items, skills, and education. Profile links and settings remain in the
  next import slice to avoid duplicating existing singleton records.
- Extended the curated seed command to upsert professional and social/contact links into
  `profile_links`; the Contact page still needs its runtime API migration.
- Migrated the Bucket List page to fetch `/bucket-list` at runtime, preserving its progress
  calculation and presentation with loading/error states.
- Reduced Groq tool payloads to compact public display fields and capped results at 20 entries to
  stay within model token-per-minute limits.
- Added backend and tool pagination with a default page size of 5. The LLM is instructed to offer
  the next page when a full page is returned and request it when the user asks for more.

## Phase 6 — Deployment

- Postgres: managed or self-hosted with a persistent volume and backups, matching what's used
  for other client deployments. Confirm the target platform's handling of persistent storage
  before deploying — do not assume any given host preserves a local volume across redeploys.
- `docker-compose` for local dev: backend, bot, Postgres.
- All secrets (Groq API key, Telegram bot token, service API key, `ADMIN_TELEGRAM_ID`, DB URL)
  via environment variables, never committed.

### Environment configuration update (2026-09-03)

- Added root `.env.example` plus `frontend/.env.example`; real `.env` files remain uncommitted.
- Backend and bot explicitly call `python-dotenv`'s `load_dotenv()` before constructing settings.
- Dotenv loading resolves the repository-root `.env` by path, so commands run from service
  subdirectories use the same configuration.
- Removed the database URL fallback. Backend settings now require the explicitly located root
  `.env`; if it is missing or cannot be loaded, startup fails with the expected path.
- Alembic now uses the same explicit root `.env` loading and rejects a missing `DATABASE_URL`
  instead of silently using the placeholder URL in `alembic.ini`.
- Added `python-dotenv` to both Python service dependency lists. Vite loads `VITE_*` variables from
  the frontend environment automatically.
- Consolidated backend and bot Python dependencies into the single root `requirements.txt`; the
  services share one environment and deployment dependency manifest.
- Storage decision: Cloudflare R2 will store uploaded certificates, CV/profile media, project
  images, and event galleries. Database records will retain object keys and public/signed URLs;
  local frontend asset files are migration source material only.
- Added a protected `POST /certificates` upload endpoint using the S3-compatible R2 API. It stores
  the resulting public object URL in the certificates table; missing R2 configuration returns a
  clear `503` response.

### Data import update (2026-09-03)

- Added `backend/scripts/seed_entries.py`, a repeatable upsert importer for the existing dev.to and
  GitHub JSON snapshots. It maps `articles` to `article` and GitHub `project`/`hobby` to the
  unified `project` type, while preserving provider/type metadata in `source`.
- The importer covers timeline snapshots only. Curated project, event, hackathon, and profile
  collections still need dedicated import mappings.
- Added `backend/scripts/seed_profile.py` for the public profile record used by the bot's identity
  lookup tool. Run it after migrations with `python -m backend.scripts.seed_profile`.

### Migration configuration fix (2026-09-03)

- Completed the missing Alembic logging sections in `backend/alembic.ini`; `alembic` now loads
  the migration environment correctly. Applying the migration still requires a reachable
  PostgreSQL server configured by `DATABASE_URL`.

### Data validation fix (2026-09-03)

- Fixed seed slug generation to collapse duplicate hyphens and added migration `0002` to repair
  slugs already imported. This prevents valid database rows from failing API response validation.

### Backend integration update (2026-09-04)

- Added configurable CORS for the frontend origin via `FRONTEND_ORIGIN`.

### Asset storage update (2026-09-04)

- Added protected generic `POST /assets` R2 upload support for profile images, CVs, project media,
  and event galleries; public `GET /assets` is the frontend lookup path.
- Added admin `/upload <asset_type> [label]` bot flow for direct R2 asset uploads. Files bypass the
  LLM and are sent through the protected backend upload endpoint.
- Added admin `/edit <entry-id> <changes>` and `/delete <entry-id>` workflows with preview and
  confirmation, using the existing protected entry mutation endpoints.
- Added admin `/profile <changes>` workflow with Groq field extraction, preview, confirmation,
  and protected profile update endpoint.
- Added protected `/admin/content` CRUD dispatch for contact links, skill groups, education,
  bucket-list items, and site settings. Added the admin bot command
  `/manage <resource> <list|create|update|delete> [JSON]`; mutations require the existing
  preview plus `/confirm` safety step, while `list` reads current database records directly
  through the backend. The bot still never connects to PostgreSQL.

### Migration cleanup update (2026-09-04)

- Removed legacy frontend-only content modules and build-time fetch/export scripts after runtime
  API migration verification. Retained local certificate/CV/profile media and `backend/data`
  snapshots as import/seeding source material; they are no longer used by the frontend runtime.

### Render deployment fix (2026-09-04)

- Made the root `.env` optional for backend, bot, and Alembic configuration. Render supplies
  required settings through environment variables and does not create a repository `.env`; local
  `.env` files remain supported, without overriding already-injected environment values.

### Render database driver fix (2026-09-04)

- Render's managed Postgres URL may use `postgres://` or `postgresql://`, which makes SQLAlchemy
  select the uninstalled psycopg2 driver by default. Normalize those URLs to the installed
  `postgresql+psycopg` driver for both application startup and Alembic migrations.

### Timeline seed deployment fix (2026-09-04)

- Made `seed_entries` tolerate missing legacy frontend snapshots. Those snapshots were removed
  after the runtime API migration, while curated timeline collections are imported by
  `seed_curated`; deployment seeding now completes successfully and reports skipped snapshots.

### Combined Render service update (2026-09-04)

- Mounted the Telegram webhook app into the backend service so the portfolio API and bot share
  one paid Render instance. The combined service starts from the repository root with
  `uvicorn backend.app.main:app`; the bot's `BACKEND_URL` points to the same backend URL.

### Production data ownership update (2026-09-04)

- Removed repository-local content snapshots, media, and seed scripts from the current tree after
  production data was populated in PostgreSQL/R2. The repository retains schema migrations and
  application code, while Render deployments now run Alembic migrations only. Historical Git
  commits remain unchanged.

### CORS origin configuration update (2026-09-04)

- Backend CORS now accepts comma-separated origins and trims trailing slashes, allowing production
  deployments to support both apex and `www` frontend domains without wildcard access.

### Security hardening update (2026-09-04)

- Limited certificate and generic asset uploads to 10 MB, rejecting oversized files before R2
  upload. Restricted the public settings endpoint to an explicit safe-key allowlist so internal
  settings such as extracted CV text cannot be exposed accidentally.

- Telegram upload instructions now display the 10 MB limit and return a clear size-specific
  message when the backend rejects an oversized file.

### Telegram response style update (2026-09-04)

- Tightened public LLM response guidance for conversational Telegram replies, including direct
  answers, less repetition, short paragraphs, and a 500-token completion cap. Clarified that file
  uploads are immediate and `/confirm` applies only to pending content changes.

### Bot grounding and CV delivery update (2026-09-04)

- Added direct CV delivery from the public CV asset when users ask to send/download/share it.
- Tightened the public assistant prompt to refuse unrelated questions and prohibit unsupported
  employers, roles, metrics, technologies, and qualifications.

- Added a dedicated public contact-links tool so the assistant can retrieve the complete verified
  professional and social contact list instead of relying on partial search matches.

### Asset cache-busting update (2026-09-04)

- R2 upload object keys now include a UUID, ensuring replacement profile images, CVs, and other
  assets receive new URLs instead of being served from a CDN-cached previous object key.

### Dynamic profile icon update (2026-09-04)

- The browser favicon and Apple touch icon now update from the current database/R2 `profile-image`
  asset, with the static frontend icon remaining as the initial fallback.

- CV delivery now verifies the downloaded asset has a PDF signature and always sends it with a
  `.pdf` filename, preventing an HTML/error response or ambiguous asset label from being presented
  as the CV.

## Open items to resolve during the work, not before

- Exact Telegram bot library (`python-telegram-bot` vs `aiogram`) — pick one during Phase 4,
  document the choice and why here.
- Exact Groq model for tool-calling — confirm current smallest tool-capable model at
  implementation time and record it here.
