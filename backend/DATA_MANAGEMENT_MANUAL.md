# Backend Data Management Manual

This manual describes how to manage portfolio data through the Telegram bot and backend API.

The recommended workflow is to use natural-language requests. The LLM interprets the request and
uses the appropriate public or administrator tools. The bot authenticates the administrator and
maintains the conversation; it does not interpret portfolio fields itself.

## Requirements

- The bot must be running.
- Your Telegram ID must match `ADMIN_TELEGRAM_ID`.
- The backend must be reachable from the bot.
- The database must be migrated to the current Alembic head.
- `SERVICE_API_KEY` must be configured for protected backend writes.

Apply migrations before using new data-management features:

```bash
cd backend
alembic upgrade head
```

## Safety model

The workflow is:

```text
Natural-language request
        ↓
LLM interprets request and calls the appropriate tools
        ↓
Low-risk change: applied immediately
        ↓
Destructive/high-impact change: confirmation requested
        ↓
Backend validates and writes to PostgreSQL
```

The LLM must not invent record IDs. For updates and deletes, it must look up the existing record
and return its exact ID. Administrator tools reject callers who are not the configured owner.

Profile edits and ordinary metadata updates do not require confirmation. Deletions, CV tailoring or
rendering, destructive asset operations, and other high-impact changes remain confirmation-protected.

## Core commands

### Natural-language administration

Send the request in ordinary language. Management commands are no longer the primary interface; the
LLM determines the target resource and operation.

```text
add my GitHub profile as a professional contact link (passed)
```

```text
update my dev.to profile link to use the professional category (passed)
```

```text
remove the old LabLab AI link (passed)
```

Low-risk updates are applied directly. Destructive requests receive a confirmation request before
the backend mutation is called.


### `/cancel`

Discards the current preview.

```text
/cancel
```

Deployments or bot restarts may clear in-memory pending previews. If that happens, resend the
original request.

## Profile details

Ask naturally for profile changes:

```text
Change my tagline to Backend engineer and set my location to Nairobi
```

Profile fields include:

- Name
- Tagline
- Location
- Focus
- Experience
- Availability status
- Availability detail
- About text

Profile text is stored in the profile record and is applied immediately. Contact details do not
belong in the profile record; the LLM stores them as profile links.

## Contact and social links

Use natural language:

```text
Set my WhatsApp, Telegram, dev.to, and LabLab AI usernames to mikesplore
```

The LLM should create or update one link per named platform. WhatsApp and Telegram default to
`contact`; dev.to and LabLab AI default to `social`. Explicit categories override these defaults.

Supported link categories:

- `professional` — work, code, writing, and professional profiles
- `social` — public social profiles
- `contact` — direct contact and messaging methods

Link records contain:

- Name
- URL
- Label
- Handle
- Category
- Visibility
- Display order

The backend normalizes link names and URLs. Repeating an existing create request upserts the link
instead of creating a duplicate.

To update a link:

```text
Update my dev.to profile link to be professional
```

To delete a link:

```text
Delete my old Telegram contact link
```

If more than one record matches, make the request more specific.

## Uploading assets

File transfer is handled directly because Telegram must provide the binary file, but the resulting
asset record and project attachment are managed through administrator tools.

```text
Upload a Vela architecture diagram
```

Then send the file as a Telegram document or image.

The upload is stored in R2 and a `site_assets` record is created. The maximum upload size is 5 MB.

To ask the administrator workflow to list uploaded assets, use:

```text
List my uploaded assets
```

After uploading, link the asset to a project:

```text
Attach the uploaded Vela architecture diagram to the Vela project as a gallery image
```

The LLM should create an `entry-assets` relationship containing the Vela entry ID and asset ID.

## Project metadata

Ask the LLM to update project metadata:

```text
set Vela status to active and category to android (passed)
```

```text
set the Vela project origin to portfolio and author role to creator (passed)
```

Project records are unified `entries` with `content_type=project`.

## Repositories

Add a repository:

```text
add https://github.com/mikesplore/vela as the primary repository for Vela (passed)
```

Update repository metadata:

```text
set the primary language of the Vela repository to Kotlin
```

Repository records can include:

- Name
- URL
- Primary flag
- Role label
- Primary language
- Link label
- GitHub sync state
- Display order

## Technologies

Attach technologies to projects through the normalized technology relationships. For example:

```text
add Kotlin, Python, FastAPI, and MCP technologies to Vela
```

Set technology metadata:

```text
set the Python technology icon to https://example.com/python.svg
```

## Project content blocks

The supported content-block resources are:

- `topology`
- `metrics`
- `decisions`
- `highlights`
- `quotes`
- `snippets`
- `documents`
- `badges`

## Regression testing checklist

Run these checks after a bot or backend deployment. Each request should be sent as ordinary
language; the examples intentionally omit management command prefixes.

### Profile safety

```text
Change my tagline to Backend engineer and set my location to Nairobi
```

Expected: the two requested fields change immediately. Existing `name`, `focus`, `experience`,
availability fields, and `about` remain unchanged.

### Contact-link classification and upsert

```text
Set my WhatsApp, Telegram, dev.to, and LabLab AI usernames to mikesplore
```

Expected: four separate links are created or updated. WhatsApp and Telegram are `contact`; dev.to
and LabLab AI are `social`. Repeating the request must not create duplicates or return a conflict.

### Exact-record updates

```text
Set the primary language of the Vela repository to Kotlin
Set the Python technology icon to https://cdn.simpleicons.org/python
Set Vela status to active and category to android
```

Expected: the LLM looks up the repository, technology, and project, then updates the exact records.
No request should be converted into a create operation.

### Assets and normalized project content

Upload an image, then send:

```text
List my uploaded assets
Attach the Vela sample asset to the Vela project as a gallery image
Show me gallery items for the Vela project
```

Expected: the asset list includes IDs and URLs; attachment uses the `entry_assets` junction; the
gallery lookup returns the attached asset and `gallery` role.

### Confirmation boundaries

Expected behavior:

- profile edits and ordinary metadata updates apply immediately;
- deletions ask for confirmation and `/cancel` leaves the record intact;
- `/confirm` applies the pending high-impact operation;
- repeating a completed deletion is reported as an already-missing record, not a traceback;
- failed writes retain enough context to retry safely.

### Failure diagnostics

If an admin request fails, the Telegram response should expose the validation reason. Check the bot
logs for the full traceback, then verify the LLM tool lookup, exact ID, selected resource, and backend
response independently. Never repair a failed update by manually guessing an ID.

Examples:

```text
add a Vela metric: 150+ MCP tools, highlighted under capability
```

```text
add a Vela architecture decision titled Separate client and backend with the explanation that the layers should evolve independently
```

```text
add a Vela highlight titled Natural language control with the description Users control devices through plain-English intents
```

```text
add this URL as Vela's primary demo document: https://vela.example.com
```

Documents are the extensible curated link section. Repository links are returned separately as
repository data; they are not stored in the removed legacy `entries.links` JSONB column.

## Vela example workflow

The repository includes a repeatable Vela fixture:

```bash
python -m backend.scripts.seed_vela_fixture
```

It creates or updates:

- `vela`
- `vela-mcp`
- `velavps`
- `vela-android`
- Their technologies and repositories
- Vela topology and metrics
- A Vela architecture decision
- A Vela highlight
- Related-project relationships

Verify the result through:

```http
GET /api/v1/projects/vela
GET /api/v1/projects/vela/media
GET /api/v1/projects/vela/relationships
```

## Direct API usage

The public project API requires no service key:

```http
GET /api/v1/projects
GET /api/v1/projects/{slug}
GET /api/v1/projects/{slug}/media
GET /api/v1/projects/{slug}/relationships
GET /api/v1/technologies
```

Protected writes require `X-Service-Api-Key` and should normally be performed by the bot.

## Troubleshooting

### The bot says it cannot find a record

Make the target explicit:

```text
update the dev.to profile link with URL https://dev.to/mikesplore
```

For updates and deletes, the LLM must identify one existing record and return its exact ID.

### The backend says `Content not found`

The operation used an invalid or missing record ID. Ensure the bot has been restarted after the
latest code deployment and retry the natural-language request.

### The backend says `duplicate`

A normalized link with the same name and URL already exists. Update the existing record instead of
creating another one.

### The backend says a column does not exist

The database is behind the application code:

```bash
cd backend
alembic upgrade head
```

### A project has no media

Upload the file first, then ask the LLM to attach the resulting asset to the project with the
appropriate role and order.

## Recommended workflow

1. Seed or create the project.
2. Add technologies and repositories.
3. Upload project assets.
4. Attach assets to the project.
5. Add content blocks one at a time or in a small batch.
6. Review the LLM's explanation for high-impact operations.
7. Confirm only when the LLM requests confirmation.
8. Verify the public API response before building or updating the independent frontend.
