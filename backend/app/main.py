from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import cast, or_, select, String
from sqlalchemy.orm import Session
from uuid import UUID

from .auth import require_service_key
from .db import get_db
from .models import Certificate, Entry, Profile
from .schemas import EntryCreate, EntryRead, EntryUpdate

app = FastAPI(title="mikesplore portfolio API", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/profile")
def get_profile(db: Session = Depends(get_db)):
    profile = db.get(Profile, 1)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {key: getattr(profile, key) for key in ("name", "tagline", "location", "focus", "experience", "availability_status", "availability_detail", "about")}


@app.get("/certificates")
def list_certificates(db: Session = Depends(get_db)):
    return db.scalars(select(Certificate).where(Certificate.is_visible.is_(True)).order_by(Certificate.custom_order)).all()


@app.get("/search")
def search_portfolio(q: str = Query(min_length=1), page: int = Query(default=1, ge=1), page_size: int = Query(default=5, ge=1, le=50), db: Session = Depends(get_db)):
    term = f"%{q}%"
    query = select(Entry).where(Entry.is_visible.is_(True), or_(Entry.title.ilike(term), Entry.blurb.ilike(term), cast(Entry.tags, String).ilike(term), cast(Entry.links, String).ilike(term))).order_by(Entry.custom_order, Entry.date.desc().nullslast())
    entries = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    profile = db.get(Profile, 1) if any(word in q.lower() for word in ("who", "michael", "person", "about", "background")) else None
    profile_data = None if not profile else {key: getattr(profile, key) for key in ("name", "tagline", "location", "focus", "experience", "availability_status", "availability_detail", "about")}
    return {"profile": profile_data, "entries": entries}


@app.get("/entries", response_model=list[EntryRead])
def list_entries(
    content_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = select(Entry).where(Entry.is_visible.is_(True)).order_by(Entry.custom_order, Entry.date.desc().nullslast())
    if content_type:
        query = query.where(Entry.content_type == content_type)
    return db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()


@app.get("/entries/{entry_id}", response_model=EntryRead)
def get_entry(entry_id: UUID, db: Session = Depends(get_db)):
    entry = db.scalar(select(Entry).where(Entry.id == entry_id, Entry.is_visible.is_(True)))
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@app.post("/entries", response_model=EntryRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_service_key)])
def create_entry(payload: EntryCreate, db: Session = Depends(get_db)):
    entry = Entry(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@app.patch("/entries/{entry_id}", response_model=EntryRead, dependencies=[Depends(require_service_key)])
def update_entry(entry_id: UUID, payload: EntryUpdate, db: Session = Depends(get_db)):
    entry = db.get(Entry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


@app.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_service_key)])
def delete_entry(entry_id: UUID, db: Session = Depends(get_db)):
    entry = db.get(Entry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
