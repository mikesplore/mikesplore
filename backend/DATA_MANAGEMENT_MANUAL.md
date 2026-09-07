# Backend Data Management Manual

This manual describes how to manage portfolio data through the Telegram bot and backend API.

The recommended workflow is to use natural-language `/admin` requests. The LLM interprets the
request and uses backend lookup tools to find existing records. The bot then shows a preview and
requires explicit confirmation before writing anything.

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
LLM interprets request and looks up records
        ↓
Preview shown in Telegram
        ↓
/confirm or /cancel
        ↓
Backend validates and writes to PostgreSQL
```

The LLM should not invent record IDs. For updates and deletes, it must look up the existing record
and return its exact ID.

## Core commands

### `/admin`

Use `/admin` for natural-language create, update, and delete requests.

```text
/admin add my GitHub profile as a professional contact link
```

```text
/admin update my dev.to profile link to use the professional category
```

```text
/admin remove the old LabLab AI link
```

The bot shows a preview. Nothing is written until `/confirm` is sent.

### `/confirm`

Applies the current preview.

```text
/confirm
```

### `/cancel`

Discards the current preview.

```text
/cancel
```

Deployments or bot restarts may clear in-memory pending previews. If that happens, resend the
original request.

### `/help`

Displays the currently available public and administrator commands.

## Profile details

Use `/profile` for profile text only:

```text
/profile Change my tagline to Backend engineer and set my location to Nairobi
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

Contact details do not belong in the profile record. Use `/admin` so they are stored as profile
links.

## Contact and social links

Use natural language:

```text
/admin add my WhatsApp, Telegram, dev.to, and LabLab AI usernames as mikesplore
```

The LLM should create multiple link records in one operation. Review the preview and confirm.

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

The backend normalizes link names and URLs and rejects duplicate identities.

To update a link:

```text
/admin update my dev.to profile link to be professional
```

To delete a link:

```text
/admin delete my old Telegram contact link
```

If more than one record matches, make the request more specific.

## Uploading assets

Uploads are handled directly and do not go through the LLM.

```text
/upload project-image Vela architecture diagram
```

Then send the file as a Telegram document or image.

The upload is stored in R2 and a `site_assets` record is created. The maximum upload size is 10 MB.

To ask the administrator workflow to list uploaded assets, use:

```text
/admin list my uploaded assets
```

After uploading, link the asset to a project:

```text
/admin attach the uploaded Vela architecture diagram to the Vela project as a gallery image
```

The LLM should create an `entry-assets` relationship containing the Vela entry ID and asset ID.

## Project metadata

Use `/admin` to update project metadata:

```text
/admin set Vela status to active and category to android
```

```text
/admin set the Vela project origin to portfolio and author role to creator
```

Project records are unified `entries` with `content_type=project`.

## Repositories

Add a repository:

```text
/admin add https://github.com/mikesplore/vela as the primary repository for Vela
```

Update repository metadata:

```text
/admin set the primary language of the Vela repository to Kotlin
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
/admin add Kotlin, Python, FastAPI, and MCP technologies to Vela
```

Set technology metadata:

```text
/admin set the Python technology icon to https://example.com/python.svg
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

Examples:

```text
/admin add a Vela metric: 150+ MCP tools, highlighted under capability
```

```text
/admin add a Vela architecture decision titled Separate client and backend with the explanation that the layers should evolve independently
```

```text
/admin add a Vela highlight titled Natural language control with the description Users control devices through plain-English intents
```

```text
/admin add this URL as Vela's primary demo document: https://vela.example.com
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
/admin update the dev.to profile link with URL https://dev.to/mikesplore
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

Upload the file first, then use `/admin` to attach the resulting asset to the project with the
appropriate role and order.

## Recommended workflow

1. Seed or create the project.
2. Add technologies and repositories.
3. Upload project assets.
4. Attach assets to the project.
5. Add content blocks one at a time or in a small batch.
6. Review every preview.
7. Confirm the operation.
8. Verify the public API response before building or updating the independent frontend.

## Extensive testing runbook

Run this section after every bot/backend deployment. Use a test or staging database where possible.
Record the result of each test as `PASS`, `FAIL`, or `BLOCKED`.

### Test prerequisites

Confirm the service is running:

```bash
curl http://127.0.0.1:8000/health
cd backend
alembic current
alembic upgrade head
```

Confirm the bot is using the expected commits and restart it after code changes. Confirm that the
administrator Telegram account matches `ADMIN_TELEGRAM_ID`.

Seed the repeatable Vela fixture:

```bash
python -m backend.scripts.seed_vela_fixture
```

Verify the fixture through the public API:

```bash
curl http://127.0.0.1:8000/api/v1/projects/vela
curl http://127.0.0.1:8000/api/v1/projects/vela/media
curl http://127.0.0.1:8000/api/v1/projects/vela/relationships
curl http://127.0.0.1:8000/api/v1/technologies
```

### Confirmation safety tests

Test every mutation with this sequence:

1. Send the `/admin` request.
2. Confirm that the preview contains the expected resource and action.
3. Confirm that update/delete previews contain an exact record ID.
4. Send `/cancel`.
5. Verify the database/API is unchanged.
6. Repeat the request.
7. Send `/confirm`.
8. Verify the expected API/database change.

Test that `/confirm` without a pending operation produces a harmless message and performs no write.
Test that `/cancel` clears the pending operation and a second `/confirm` cannot apply it.
Test that a non-admin Telegram account cannot enter the admin workflow.

### Asset tests

List assets:

```text
/admin list my assets
```

Expected behavior:

- The bot calls the asset lookup tool.
- The response is a compact human-readable list.
- It includes asset ID, type, label, and URL.
- PDFs are represented by metadata only; binary file contents are not sent to the LLM.

Upload a project image:

```text
/upload project-image Vela gallery test
```

Then send a small image file. Verify that the response includes an asset label and that the asset
appears in `/admin list my assets`.

Attach it to Vela:

```text
/admin attach the Vela gallery test asset to Vela as a gallery image
```

Expected preview fields:

- Resource: `entry-assets`
- Action: `create`
- Exact Vela `entry_id`
- Exact asset `asset_id`
- Role: `gallery`

Confirm and verify:

```text
/admin show me gallery items for the Vela project
```

Repeat the same attach request. It should upsert rather than create a duplicate.

### Project tests

List project records:

```text
/admin list my projects
```

Update project metadata:

```text
/admin set Vela status to active and category to android
```

The preview must identify the Vela entry ID and only contain the requested fields.

Test an ambiguous project request:

```text
/admin update the project status to production
```

Expected behavior: the bot asks for a specific project rather than selecting one arbitrarily.

### Repository tests

List repositories:

```text
/admin list my repositories
```

Create a repository:

```text
/admin add https://github.com/example/new-repo as a repository for Vela
```

The LLM must look up the project and repository URL before creating it. If the name is omitted,
the backend may derive it from the URL.

Repeat the same request. Expected behavior: the existing URL is detected and the operation becomes
an update/upsert, not a duplicate create.

Update repository metadata:

```text
/admin set the primary language of the Vela repository to Kotlin
```

The preview must contain the existing repository ID. Confirm and verify `/api/v1/projects/vela`.

### Technology tests

List technologies:

```text
/admin list my technologies
```

Attach technologies to Vela:

```text
/admin add Kotlin, Python, FastAPI, and MCP technologies to Vela
```

Expected behavior:

- The LLM calls project and technology lookup tools.
- It uses `entry-technologies`, never `topology`.
- The preview includes exact project and technology IDs.
- Repeating the request does not create duplicate junction rows.

Update technology metadata:

```text
/admin set the Python technology icon to https://example.com/python.svg
```

Expected behavior: the existing technology is updated/upserted by name.

### Content-block tests

For every content-block type, verify that `entry_id` is present in the preview.

Metric:

```text
/admin add a Vela metric: 150+ MCP tools, highlighted under capability
```

Architecture decision:

```text
/admin add a Vela architecture decision titled Separate client and backend with the explanation that the layers should evolve independently
```

Highlight:

```text
/admin add a Vela highlight titled Natural language control with the description Users control devices through plain-English intents
```

Topology:

```text
/admin add a Vela topology step for the backend titled Intent routing with description The backend translates user intent into a device operation
```

Quote:

```text
/admin add a Vela quote: "Remote control should feel immediate" attributed to Portfolio owner
```

Code snippet:

```text
/admin add a Vela Python code snippet labeled Intent handler
```

Document/demo link:

```text
/admin add https://example.com as Vela's primary demo document
```

Badge:

```text
/admin add a Vela badge labeled MCP compatible with style accent
```

For each type, test create, repeat, update, and delete. Missing `entry_id` must produce a clear
validation response, never a database 500.

### Contact-link tests

Create multiple links:

```text
/admin my WhatsApp, Telegram, dev.to, and LabLab AI usernames are all mikesplore
```

Expected behavior: one preview containing multiple `links` create operations or an equivalent bulk
operation. Confirm and verify `/profile/links`.

Update by natural language:

```text
/admin update my dev.to profile link to be professional
```

The LLM must look up the full profile-link collection and return the exact link ID.

Repeat the same request. It should update the existing record without creating a duplicate.

Delete by natural language:

```text
/admin delete my old LabLab AI link
```

If multiple links match, the bot must ask for clarification.

### Negative and malformed-input tests

Test these requests and expect safe rejection:

```text
/admin update a link without identifying which link
/admin delete record 00000000-0000-0000-0000-000000000000
/admin add a profile field called telegram
/admin attach an unknown asset to Vela
/admin add a metric without naming a project
/admin add a repository without a URL
```

Expected behavior:

- No database 500 errors
- No guessed IDs
- No partial bulk writes
- A clear correction or clarification message

### Public API verification after mutations

After confirming project changes, check:

```bash
curl http://127.0.0.1:8000/api/v1/projects/vela
curl http://127.0.0.1:8000/api/v1/projects/vela/media
curl http://127.0.0.1:8000/api/v1/projects/vela/relationships
```

Verify that:

- Hidden projects do not appear publicly.
- Child content is hidden when its parent project is hidden.
- Technologies include IDs, categories, and icon URLs.
- Media contains the expected role, caption, alt text, and order.
- Relationships hydrate visible target entries, repositories, and technologies.
- Pagination and `X-Total-Count` behave consistently.

### Common failure diagnosis

- `json mode cannot be combined with tool/function calling`: remove JSON response format from the
  tool-enabled LLM call.
- `Request too large`: reduce lookup result fields and result count before sending them to the LLM.
- `Unterminated string`: the model output was truncated; use a structured final function tool rather
  than free-form JSON.
- `Content not found`: an update/delete operation lacks the exact existing record ID.
- `null value violates not-null constraint`: the LLM omitted a required parent ID; add or fix the
  relevant lookup tool and backend validation.
- Recursive FastAPI JSON encoding: serialize ORM attributes using mapped attribute keys, not raw
  database column names such as `metadata`.
- Duplicate conflict: verify the resource's upsert identity and repeat the request after checking
  the existing record.
