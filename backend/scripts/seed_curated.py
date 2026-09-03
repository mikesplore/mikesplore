"""Import exported curated frontend collections into the database."""
import json
import re
from datetime import date
from pathlib import Path
from sqlalchemy import select
from backend.app.db import SessionLocal
from backend.app.models import BucketListItem, Education, Entry, ProfileLink, SkillGroup, SiteSetting

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend" / "data"

def slug(value):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")[:160]

def entry_payload(item, content_type):
    if content_type == "project":
        return {"slug": slug(item["id"]), "content_type": "project", "title": item["title"], "blurb": item["summary"], "is_visible": True, "details": {"tagline": item.get("tagline"), "overview": item.get("overview"), "details": item.get("details"), "platform": item.get("platform"), "type": item.get("type"), "status": item.get("status")}, "tech_stack": item.get("stack", []), "tags": item.get("tags", []), "links": item.get("links", {}), "media": {"cardImage": item.get("cardImage"), "gallery": item.get("gallery", [])}, "source": {"provider": "curated-frontend"}}
    return {"slug": slug(f"{content_type}-{item['title']}-{item.get('year', item.get('date', ''))}"), "content_type": content_type, "title": item["title"], "blurb": item.get("description", item.get("blurb", "")), "date": date.fromisoformat(item["date"]) if item.get("date") else None, "year": int(item["year"]) if str(item.get("year", "")).isdigit() else None, "is_visible": True, "details": {key: item[key] for key in ("result", "project", "organization", "location") if item.get(key)}, "links": {"url": item["link"]} if item.get("link") else {}, "media": {"image": item.get("image"), "photos": item.get("photos", [])}, "source": {"provider": "curated-frontend"}}

def main():
    db = SessionLocal()
    try:
        for content_type, filename, key in (("project", "projects", "projects"), ("event", "events", "events"), ("hackathon", "hackathons", "hackathons")):
            for item in json.loads((DATA / f"{filename}.json").read_text()):
                payload = entry_payload(item, content_type)
                existing = db.scalar(select(Entry).where(Entry.slug == payload["slug"]))
                if existing:
                    for field, value in payload.items(): setattr(existing, field, value)
                else: db.add(Entry(**payload))
        for order, item in enumerate(json.loads((DATA / "bucketListItems.json").read_text())):
            existing = db.get(BucketListItem, item["id"])
            if not existing: existing = BucketListItem(id=item["id"]); db.add(existing)
            existing.title, existing.done, existing.remark, existing.custom_order = item["title"], item["done"], item.get("remark"), order
        for order, item in enumerate(json.loads((DATA / "skillsGrouped.json").read_text())): db.add(SkillGroup(category=item["category"], skills=item["skills"], custom_order=order))
        for order, item in enumerate(json.loads((DATA / "education.json").read_text())): db.add(Education(**item, custom_order=order))
        for category, filename in (("professional", "socialLinks"), ("social", "contactSocials")):
            for order, item in enumerate(json.loads((DATA / f"{filename}.json").read_text())):
                existing = db.scalar(select(ProfileLink).where(ProfileLink.name == item["name"], ProfileLink.category == category))
                payload = {"name": item["name"], "url": item["url"], "label": item.get("label"), "handle": item.get("handle"), "category": category, "custom_order": order, "is_visible": True}
                if existing:
                    for field, value in payload.items(): setattr(existing, field, value)
                else: db.add(ProfileLink(**payload))
        db.commit(); print("Imported curated projects, events, hackathons, bucket list, skills, education, and contact links")
    finally: db.close()

if __name__ == "__main__": main()
