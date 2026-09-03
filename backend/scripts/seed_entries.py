"""Import the existing frontend timeline snapshots into the backend."""
import json
import re
from datetime import date
from pathlib import Path

from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import Entry

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "frontend" / "src" / "data"

def slugify(title: str, link: str = "") -> str:
    value = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    suffix = re.sub(r"[^a-z0-9]+", "-", link.lower()).strip("-")[-24:]
    return f"{value}-{suffix}".strip("-")[:160]

def load_snapshot(filename: str, source_name: str) -> list[dict]:
    records = json.loads((DATA_DIR / filename).read_text())
    for record in records:
        record["_source_name"] = source_name
    return records

def to_entry(record: dict) -> dict:
    content_type = {"articles": "article", "project": "project", "hobby": "project"}.get(record["type"])
    if not content_type:
        raise ValueError(f"Unsupported source type: {record['type']}")
    link = record.get("link") or ""
    return {
        "slug": slugify(record["title"], link), "content_type": content_type,
        "title": record["title"], "blurb": record.get("blurb") or "",
        "date": date.fromisoformat(record["date"]) if record.get("date") else None,
        "is_visible": True, "is_featured": False, "custom_order": 0,
        "tech_stack": record.get("tags") or [], "tags": record.get("tags") or [],
        "details": {key: record[key] for key in ("stars", "readTime") if key in record},
        "links": {"url": link} if link else {},
        "media": {"thumbnail": record["thumbnail"]} if record.get("thumbnail") else {},
        "source": {"provider": record["_source_name"], "original_type": record["type"]},
    }

def main() -> None:
    records = load_snapshot("entries.devto.json", "dev.to") + load_snapshot("entries.github.json", "github")
    db = SessionLocal()
    try:
        for payload in map(to_entry, records):
            entry = db.scalar(select(Entry).where(Entry.slug == payload["slug"]))
            if entry:
                for key, value in payload.items():
                    setattr(entry, key, value)
            else:
                db.add(Entry(**payload))
        db.commit()
        print(f"Imported {len(records)} timeline entries")
    finally:
        db.close()

if __name__ == "__main__":
    main()
