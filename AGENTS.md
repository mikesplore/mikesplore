# AGENTS.md — Portfolio Backend + Telegram Bot Conversion

This file tracks the phased conversion of mikesplore.me from a static, build-time-sourced
portfolio into a database-driven system served by a FastAPI backend, consumed by both the
existing frontend and a Telegram bot. Update this file as you go: log what you actually did,
any deviations from the plan below, and why. Do not silently diverge from the plan without
recording it here — this project has diverged from its plan before (multi-tab nav instead of
collapsed, always-expanded cards instead of accordion) without being written down until later,
which cost time to reconcile.

## Architecture summary

- **Repo**: single monorepo. Subdirectories: `backend/`, `bot/`, `frontend/`.
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

Do this before writing any schema or backend code.

- Read through the existing frontend repo/codebase in full: `portfolio.js`, the `TimelineEntry`
  TypeScript model, and however build-time content sourcing from the dev.to and GitHub APIs is
  currently wired up.
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

- Repository layout differs from the architecture summary: the existing Vite/React frontend is
  at the repository root (`src/`, `scripts/`, `public/`); `backend/`, `bot/`, and `frontend/`
  do not exist yet.
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
  override for selected repositories. `src/data/entries.js` merges both generated JSON files,
  deduplicates by normalized link/title, and sorts newest first.
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

## Phase 2 — Backend API (FastAPI)

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

- Project skeleton: FastAPI + SQLAlchemy + Alembic, Pydantic schemas matching the Phase 1 schema.
- Public endpoints (no auth): `GET` list and detail routes, filtered to `is_visible = true`,
  ordered by `custom_order`.
- Protected write endpoints (service API key required): create/update/delete on entries. These
  are the endpoints the bot's admin path calls — never called by the public frontend.
- Write basic tests for the visibility filter (a visible=false entry must never appear on a
  public endpoint) before moving on — this is the one bug that would defeat the entire point of
  curation.

## Phase 3 — Frontend migration

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

- Replace the build-time GitHub/dev.to fetching with runtime fetch calls to the backend's public
  endpoints.
- Visual output must not change. This is a data-source swap, not a redesign.
- Remove the now-dead build-time sourcing code rather than leaving it dormant.

## Phase 4 — Telegram bot: public read path

- Bot skeleton with webhook-based updates (not long-polling).
- LLM tool-calling setup: define tools that call the backend's public REST endpoints. The model
  answers questions by calling these tools, not by generating facts from its own training data.
- Keep a couple of hardcoded commands (`/start`, `/help`) for basic navigation; route actual
  content questions through the LLM tool-calling path rather than building a parallel hardcoded
  command menu for each content type.

## Phase 5 — Telegram bot: admin write path

- Middleware: reject any write-path command where `message.from.id != ADMIN_TELEGRAM_ID`.
- Accept a document or free-text instruction from the admin, use the LLM to extract structured
  fields matching the Phase 1 schema.
- Show a preview of the extracted data and require explicit confirmation before the bot calls
  the backend's protected write endpoint. This confirm step is the actual safety net against bad
  extractions — treat it as required, not optional polish.
- No GitHub webhook auto-sync in this phase. Ingestion is document/instruction-driven only, by
  design — the point is curation, not mirroring every repo.

## Phase 6 — Deployment

- Postgres: managed or self-hosted with a persistent volume and backups, matching what's used
  for other client deployments. Confirm the target platform's handling of persistent storage
  before deploying — do not assume any given host preserves a local volume across redeploys.
- `docker-compose` for local dev: backend, bot, Postgres.
- All secrets (Groq API key, Telegram bot token, service API key, `ADMIN_TELEGRAM_ID`, DB URL)
  via environment variables, never committed.

## Open items to resolve during the work, not before

- Exact Telegram bot library (`python-telegram-bot` vs `aiogram`) — pick one during Phase 4,
  document the choice and why here.
- Exact Groq model for tool-calling — confirm current smallest tool-capable model at
  implementation time and record it here.
