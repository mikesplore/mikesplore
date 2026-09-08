"""Provider source synchronization (Dev.to and GitHub) used by the admin sync routes."""

import re

import httpx
from fastapi import HTTPException
from sqlalchemy import cast, select, String
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Entry


def slugify(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")[:100]


def source_entry(source: str, item: dict, visible: bool) -> dict:
    if source == "devto":
        url = item.get("url") or item.get("canonical_url")
        title = item.get("title", "Untitled article")
        return {
            "slug": slugify(title),
            "content_type": "article",
            "title": title,
            "blurb": item.get("description") or item.get("description_markdown") or "",
            "date": (item.get("published_at") or item.get("created_at", ""))[:10] or None,
            "is_visible": True,
            "tags": item.get("tag_list", []),
            "source": {"provider": "dev.to", "key": url, "body_markdown": item.get("body_markdown") or item.get("body_html") or ""},
        }
    url = item.get("html_url")
    title = item.get("name", "Untitled repository")
    return {
        "slug": slugify(title),
        "content_type": "project",
        "title": title,
        "blurb": item.get("description") or "",
        "date": (item.get("created_at", ""))[:10] or None,
        "is_visible": visible,
        "tags": [],
        "source": {"provider": "github", "key": url, "repo": item.get("full_name")},
    }


async def fetch_source(source: str, username: str | None = None) -> list[dict]:
    if source not in {"devto", "github"}:
        raise HTTPException(status_code=400, detail="Source must be devto or github")
    username = username or (settings.devto_username if source == "devto" else settings.github_username)
    if not username:
        raise HTTPException(status_code=503, detail=f"{source} username is not configured")
    url = (f"https://dev.to/api/articles?username={username}&per_page=100" if source == "devto"
           else f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated")
    headers = {"Accept": "application/vnd.github+json"}
    if source == "github" and settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


def apply_sync(db: Session, source: str, payload: dict) -> dict:
    """Upsert an approved preview. Source URLs are the idempotency key."""
    if source not in {"devto", "github"}:
        raise HTTPException(status_code=400, detail="Source must be devto or github")
    selected = set(payload.get("selected", []))
    items = payload.get("items", [])
    changed = []
    for data in items:
        key = (data.get("source") or {}).get("key")
        if not key:
            continue
        entry = db.scalar(select(Entry).where(cast(Entry.source, String).ilike(f"%{key}%")))
        if not entry:
            # Keep the source URL as identity and avoid normalized-slug collisions.
            slug = data.get("slug") or "github-entry"
            if db.scalar(select(Entry).where(Entry.slug == slug)):
                repo_name = (data.get("source") or {}).get("repo") or data.get("title") or "repo"
                slug = slugify(f"{slug}-{repo_name}")[:160]
                suffix = 2
                while db.scalar(select(Entry).where(Entry.slug == slug)):
                    slug = slugify(f"{slug}-{suffix}")[:160]
                    suffix += 1
            data = {**data, "slug": slug}
            entry = Entry(**data)
            db.add(entry)
        else:
            # Imported fields may refresh, but editorial fields and GitHub selection survive.
            old_visible = entry.is_visible
            for field in ("title", "blurb", "date", "tags", "source"):
                setattr(entry, field, data[field])
            entry.is_visible = old_visible if source == "github" and key not in selected else (key in selected if source == "github" else True)
        if source == "github" and key in selected:
            entry.is_visible = True
        changed.append({"title": data.get("title"), "key": key, "visible": entry.is_visible})
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="GitHub sync could not be saved. Check for duplicate repository slugs or invalid repository metadata.")
    return {"source": source, "updated": len(changed), "items": changed}