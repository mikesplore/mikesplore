# Independent Projects Site Plan

## Objective

Create a separate projects website that renders entirely from the portfolio database through
public API endpoints. The site should not import frontend files, access PostgreSQL directly, or
depend on the main portfolio site's layout and components.

## Current foundation

The backend already provides or stores:

- Unified project entries in `entries`
- Project metadata such as status, version, license, category, origin, and dates
- Normalized technologies and entry-technology relationships
- Repository records
- Visibility, featured state, and custom ordering
- Content-block tables for project details
- A relationships graph
- Public project and technology endpoints

## Required backend work before building the site

### 1. Stabilize the public API contract

Expose a versioned contract, preferably under `/api/v1`, with a response shape independent of
database table names.

Recommended project response:

```json
{
  "id": "uuid",
  "slug": "vela",
  "title": "Vela",
  "summary": "...",
  "status": "production",
  "version": "...",
  "license": "...",
  "category": "tooling",
  "origin": "...",
  "started_at": "2025-01-01",
  "ended_at": null,
  "technologies": [],
  "repositories": [],
  "links": {},
  "media": [],
  "content": {
    "topology": [],
    "metrics": [],
    "decisions": [],
    "highlights": [],
    "quotes": [],
    "snippets": [],
    "documents": [],
    "badges": []
  },
  "relationships": []
}
```

The independent site should consume this contract rather than reproduce database assumptions.

### 2. Complete content-block support

The database contains content-block tables, but the API must expose all of them:

- Topology steps
- Metrics
- Architecture decisions
- Highlights
- Quotes
- Code snippets
- Documents
- Badges

Add ORM models and serializers for any content-block tables not currently represented in
`backend/app/models.py`.

### 3. Add project media relationships

Projects need a normalized media relationship for:

- Card images
- Logos and icons
- Screenshots
- Galleries
- Architecture diagrams
- Videos or demos

Use `entry_assets` as a junction to the existing `site_assets` table. Do not create a second asset
store. The junction should contain:

- `id`
- `entry_id` → `entries.id`
- `asset_id` → `site_assets.id`
- `role`
- `alt_text`
- `caption`
- `custom_order`
- `is_visible`

The existing `site_assets` table remains the owner of uploaded asset URLs and labels. `entry_assets`
only describes how an asset is used by a project.

### 4. Expose relationships

Add a public endpoint such as:

```http
GET /api/v1/projects/{slug}/relationships
```

Return related projects, repositories, and technologies with enough display information for the
site to render links without additional database knowledge. Because `relationships` stores only
typed IDs, the endpoint must hydrate each target according to `object_type`:

- `entry` → query `entries`
- `repository` → query `repositories`, then its parent entry if display context is needed
- `technology` → query `technologies`

Apply target visibility checks during hydration. A relationship to a hidden entry or hidden parent
must not appear publicly.

### 5. Expose normalized technologies

Add `icon_url TEXT` to `technologies` in a follow-up migration, then return technology records with:

- Name
- Category
- Icon or logo reference
- Display order where needed

Projects should expose their technologies in display order, not only as a list of names.

### 6. Add filtering and pagination

The public API should support:

- `slug`
- `category`
- `status`
- `technology`
- `featured`
- `page`
- `page_size`

Responses should include a total count or pagination metadata.

### 7. Define public visibility behavior

Every public project endpoint must exclude `is_visible = false` records, including:

- Projects
- Repositories
- Content blocks
- Media
- Relationships where appropriate

Draft or incomplete content should never leak through a related endpoint.

### 8. Add API documentation and versioning

Document the response schemas and examples in the backend OpenAPI output and maintain a short
human-readable API contract for the independent site's development.

### 7. Decide visibility behavior

Use parent visibility cascading rather than adding `is_visible` to every child table. The current
schema does not provide per-row visibility for repositories or content blocks. Public endpoints
must exclude all child records when their parent entry has `is_visible = false`; individual child
visibility is not part of this design.

Repositories should remain controlled by the parent project visibility. Documents and assets should
also be hidden when their parent entry is hidden.

## Data population work

Populate each project consistently with:

- Project title and summary
- Status and category
- Start/end dates where known
- Technologies
- Repository records
- Demo and external links
- Media/assets
- Content blocks
- Relationships to hackathons, technologies, and related projects

Use the historical project catalog as recovery/source material, but create a repeatable importer or
admin workflow rather than manually entering records directly in PostgreSQL.

### Links versus documents

Keep the project response contract split intentionally:

- Top-level `links` contains a small fixed quick-access set such as `github`, `demo`, or `live`.
- `content.documents` contains the extensible curated document section with title, URL, icon,
  link style, and order.

The top-level quick-access links must be sourced from normalized repository records or an explicit
normalized project-link representation. They must not depend on the removed `entries.links` JSONB
column. `documents` is the richer, ordered content-block collection.

## Independent site requirements

The new site should:

- Use only the public API
- Read its API base URL from environment configuration
- Never import `frontend/src` from this repository
- Never connect directly to PostgreSQL
- Handle loading, empty, error, and unavailable-content states
- Render optional content blocks only when present
- Use slugs and API-provided IDs for stable links
- Cache public project responses where appropriate
- Avoid assuming every project has every content block

Suggested client modules:

- `projectsApi`
- `projectViewModel`
- `projectContentRenderer`
- `projectMediaRenderer`
- `technologyRenderer`
- `relationshipRenderer`

## Recommended implementation order

0. Complete and verify migrations through `0011_cleanup_legacy`, including the JSONB cutover and
   project-table removal. This is a hard prerequisite for the independent-site API work.
1. Add the `entry_assets` junction migration and the `technologies.icon_url` migration.
2. Finalize and version the project response contract.
3. Add missing content-block ORM models and serializers.
4. Add normalized project media endpoints using `site_assets` plus `entry_assets`.
5. Add hydrated relationships and technology endpoints.
6. Add filtering, pagination, visibility checks, and OpenAPI documentation.
7. Populate and verify a complete project record.
8. Build the independent site against one project first.
9. Expand to all projects and test incomplete/empty project records.

## Acceptance criteria

The independent site is ready to build when:

- One `GET /api/v1/projects/{slug}` response contains everything needed for a complete project
  page.
- No project details require a legacy JSONB field or direct database access.
- All content blocks and media are optional but consistently shaped.
- Hidden projects and hidden related content never appear publicly.
- The API contract is documented and stable enough for a separate deployment.
- A complete project page can be rendered by deleting or stopping the main portfolio frontend.
