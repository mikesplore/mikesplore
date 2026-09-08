"""Protected Dev.to / GitHub source preview and apply endpoints."""

import re

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import require_service_key
from ..config import settings
from ..db import get_db
from ..models import ProfileLink
from ..services.sync import apply_sync as apply_sync_service, fetch_source, source_entry

router = APIRouter(tags=["admin"])


@router.get("/admin/sync/{source}", dependencies=[Depends(require_service_key)])
async def preview_sync(source: str, db: Session = Depends(get_db)):
    """Fetch source data without changing the database; the bot shows this result for approval."""
    try:
        username = None
        if source == "devto" and not settings.devto_username:
            link = db.scalar(select(ProfileLink).where(func.lower(ProfileLink.name) == "dev.to", ProfileLink.is_visible.is_(True)))
            if link:
                match = re.search(r"dev\.to/([^/?#]+)", link.url or "", re.IGNORECASE)
                username = match.group(1) if match else None
        items = await fetch_source(source, username)
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"{source} fetch failed: {error}")
    return {"source": source, "items": [source_entry(source, item, source == "devto") for item in items]}


@router.post("/admin/sync/{source}", dependencies=[Depends(require_service_key)])
def apply_sync_route(source: str, payload: dict, db: Session = Depends(get_db)):
    """Upsert an approved preview. Source URLs are the idempotency key."""
    return apply_sync_service(db, source, payload)