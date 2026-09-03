from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from .auth import require_service_key
from .db import get_db
from .models import Entry
from .schemas import EntryCreate, EntryRead, EntryUpdate

app = FastAPI(title="mikesplore portfolio API", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/entries", response_model=list[EntryRead])
def list_entries(content_type: str | None = None, db: Session = Depends(get_db)):
    query = select(Entry).where(Entry.is_visible.is_(True)).order_by(Entry.custom_order, Entry.date.desc().nullslast())
    if content_type:
        query = query.where(Entry.content_type == content_type)
    return db.scalars(query).all()


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
