# Portfolio Data Management Manual

This is the authoritative guide for managing portfolio data through Telegram.

The interface is LLM-first: write requests in ordinary language. The LLM selects a public or
administrator function, looks up existing records when needed, and sends validated operations to
the backend. The bot handles Telegram identity, files, confirmations, and presentation; it does
not guess database IDs or classify requests with regular expressions.

## Interface and authorization

Only these slash commands are supported:

- `/start` starts the assistant.
- `/cancel` cancels a pending destructive or high-impact action.

Do not use retired commands such as `/admin`, `/profile`, `/manage`, `/upload`, `/edit`, `/delete`,
`/cv`, `/apply`, `/confirm`, or `/help`. Send requests as normal language.

Visitors receive public read tools only. The configured portfolio owner receives administrator
tools. Administrator tools verify authorization before writes, and all writes go through the
backend service API. The bot never connects directly to PostgreSQL.

The normal flow is:

```text
Natural-language request → LLM function call → lookup if needed → backend validation → result
```

Profile edits and ordinary metadata updates apply immediately. Deletions, CV rendering, and other
high-impact operations request confirmation through an inline Telegram button. Use `/cancel` to
discard a pending action.

## Local requirements

- Bot and backend running.
- `ADMIN_TELEGRAM_ID` set to the owner's Telegram ID.
- `SERVICE_API_KEY` configured for protected backend calls.
- PostgreSQL reachable and migrations current.
- R2 configured for uploads.

```bash
cd backend
alembic upgrade head
```

Run tests with the repository virtual environment:

```bash
.venv/bin/python -m pytest -q backend/tests
```

## Profile details

Profile text belongs in the profile record:

```text
Change my tagline to Backend engineer and set my location to Nairobi
```

Supported fields include name, tagline, location, focus, experience, availability status,
availability detail, and about text. Updates are partial: changing two fields must preserve every
other field. Contact methods and social profiles belong in profile links, not profile text.

## Contact and social links

```text
Set my WhatsApp, Telegram, dev.to, and LabLab AI usernames to mikesplore
```

The LLM should resolve one complete link per named platform. Default categories are WhatsApp and
Telegram as `contact`, and dev.to and LabLab AI as `social`. An explicit category overrides the
default:

```text
Add my GitHub profile as a professional contact link
```

Links contain name, URL, label, handle, category, visibility, and display order. Repeating an
existing create request upserts the normalized link instead of duplicating it.

```text
Update my dev.to profile link to professional
Delete my old Telegram contact link
```

Updates and deletes must use an exact ID returned by a lookup. If multiple records match, the
assistant must ask for clarification.

## Projects, repositories, and technologies

Projects are unified `entries` with `content_type=project`:

```text
Set the Vela project status to active and category to android
```

Repositories are normalized records connected to entries:

```text
Add https://github.com/mikesplore/vela as the primary repository for Vela
Set the primary language of the Vela repository to Kotlin
```

Repository URLs are idempotent: an existing URL must be updated, never duplicated.

Technologies are normalized and reused:

```text
Add Kotlin, Python, FastAPI, and MCP technologies to Vela
Set the Python technology icon to https://cdn.simpleicons.org/python
```

The LLM must resolve project and technology IDs and use `entry-technologies` for relationships,
not `topology`.

## Project content blocks

Supported normalized content-block resources are `topology`, `metrics`, `decisions`, `highlights`,
`quotes`, `snippets`, `documents`, and `badges`. Every block requires the exact project
`entry_id`; the LLM must list projects before creating or updating one.

```text
Add a Vela metric: 150+ MCP tools, highlighted under capability
Add a Vela architecture decision titled Separate client and backend, explaining that the layers should evolve independently
Add a Vela highlight titled Natural language control, describing users controlling devices through plain-English intents
Add this URL as Vela's primary demo document: https://vela.example.com
```

## Assets and uploads

Request uploads naturally:

```text
I need to change my profile picture
I want to upload a gallery image for the Vela project
Upload a certificate for my Backend Engineering course
```

The LLM calls an upload-request function with the asset type and, for project media, the target
project and role. The assistant briefly asks for the file. Attach the image, PDF, or document in
the next Telegram message. The binary bypasses the LLM and is uploaded directly to R2.

The upload limit is 5 MB. Asset types include profile images, CVs, certificates, project images,
and project media. PDFs are not sent to the LLM merely because they appear in an asset listing.

Attach an existing asset to a project with:

```text
Attach the Vela sample asset to the Vela project as a gallery image
List my uploaded assets
Show me gallery items for the Vela project
Show me the next gallery image
```

Attachments use the `entry_assets` junction pointing to an existing `site_assets` record. Results
should emphasize labels, roles, captions, and view buttons; internal IDs are for tool operations.

## Dynamic role policies

Role policies are stored in `role_policies` and are derived from verified CV and portfolio data,
not hardcoded role assumptions.

```text
Analyze my current CV and portfolio data and propose supported role policies
List my role policies
Activate the backend engineering and mobile development policies
```

New proposals are saved as `pending` with `is_active=false`. The LLM must not invent evidence or
activate policies automatically. Activation uses exact IDs returned by a role-policy lookup.
Repeated analysis upserts by role family instead of creating duplicates.

## CV tailoring

Paste a job description directly, without a command prefix:

```text
[paste the complete job description]
```

The LLM recognizes a bare JD, compares it with verified CV context and active role policies, and
proposes a patch containing a professional summary, selected projects, selected skills, and any
limitations. Respond naturally to revise it, for example `emphasize backend reliability` or `that
looks good`.

High-impact rendering requires an inline confirmation button. Rendering is deterministic after
approval, the PDF is delivered through Telegram, and the base CV remains unchanged.

Groq errors are handled explicitly: `413` means the request is too large, `429` means wait and
retry, `5xx` means the provider is temporarily unavailable, and `400` means the request format
must be corrected.

## Vela verification

Vela is the reference project for testing relationships and rich content. Seed locally with:

```bash
.venv/bin/python -m backend.scripts.seed_vela_fixture
```

Then test:

```text
Show me the Vela project
List Vela's repositories
List Vela's technologies
Show me gallery items for Vela
Show me the next gallery image
```

The fixture covers Vela, vela-mcp, velavps, vela-android, technologies, repositories, content
blocks, and asset relationships.

## End-to-end testing checklist

### Authorization

- A visitor can read public portfolio data but cannot write.
- The owner receives administrator tools.
- Authorization comes from trusted Telegram context, not message wording.

### Profile and links

- Update two profile fields and verify all other fields survive.
- Create the four-platform link request twice and verify no duplicates.
- Update a link and verify the exact row changes.
- Delete a link with the inline confirmation button.
- Repeat the deletion and verify a clear not-found response, not a traceback.

### Normalized content

- Update Vela metadata and verify update rather than create.
- Add technologies and verify normalized rows are reused.
- Add a repository by URL twice and verify upsert behavior.
- Add metrics, decisions, highlights, and documents with Vela's exact entry ID.

### Assets

- Upload a profile image under 5 MB.
- Try a file over 5 MB and verify a clear size error.
- Upload project media, attach it to Vela, list the gallery, and view an image.
- Confirm PDFs are not included in LLM context unless a specific extraction flow requires them.

### CV and policies

- Paste a bare technical JD and verify tailoring starts without a command.
- Generate policies and verify they are pending and inactive.
- Activate selected policies and verify exact rows become active.
- Approve rendering and verify PDF delivery without changing the base CV.

### Telegram reliability

- Click a confirmation button after a slow request and verify no webhook 500 occurs.
- Verify callback buttons are acknowledged before slow backend work.
- Verify failed mutations remain retryable.
- Verify next/previous pagination performs a direct backend query and no new LLM request.

## Direct API and troubleshooting

Public project endpoints require no service key:

```text
GET /api/v1/projects
GET /api/v1/projects/{slug}
GET /api/v1/projects/{slug}/media
GET /api/v1/projects/{slug}/relationships
GET /api/v1/technologies
```

Protected writes require `X-Service-Api-Key` and should normally be performed by the bot.

When a request fails, inspect: the LLM function selected, lookup IDs returned, and backend status
and response body. Common causes:

- `Content not found`: stale or missing record ID.
- `409`: create used where an existing normalized record should be updated.
- `422`: required data such as `entry_id` is missing.
- `413`: upload or LLM request exceeded its limit.
- `429`: Groq rate limiting.
- Telegram `query is too old`: callback acknowledgement happened too late; use the latest bot
  build, which acknowledges callbacks before slow operations.

Do not repair failures by guessing IDs or editing PostgreSQL manually. Fix the lookup, function
schema, validation, or backend handler so the same natural-language request works reliably.
