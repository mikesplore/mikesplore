"""Protected admin content management, bulk link mutations, admin search, and entry CRUD."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import require_service_key
from ..db import get_db
from ..models import (
    ArchitectureDecision,
    Badge,
    BucketListItem,
    Certificate,
    CodeSnippet,
    Document,
    Education,
    Entry,
    EntryAsset,
    EntryTechnology,
    Highlight,
    Metric,
    ProfileLink,
    Quote,
    Repository,
    RolePolicy,
    SiteAsset,
    SiteSetting,
    SkillGroup,
    Technology,
    TopologyStep,
)
from ..schemas import BulkLinkMutation, EntryCreate, EntryRead, EntryUpdate, ProfileLinkCreate, ProfileLinkUpdate
from ..services.search import model_record

router = APIRouter(tags=["admin"])


@router.post("/admin/content", dependencies=[Depends(require_service_key)])
def manage_content(resource: str, action: str, payload: dict, response: Response, db: Session = Depends(get_db)):
    models = {"entries": Entry, "certificates": Certificate, "assets": SiteAsset, "links": ProfileLink, "skills": SkillGroup, "education": Education, "bucket-list": BucketListItem, "settings": SiteSetting, "role-policies": RolePolicy, "entry-assets": EntryAsset, "entry-technologies": EntryTechnology, "repositories": Repository, "technologies": Technology, "topology": TopologyStep, "metrics": Metric, "decisions": ArchitectureDecision, "highlights": Highlight, "quotes": Quote, "snippets": CodeSnippet, "documents": Document, "badges": Badge}
    model = models.get(resource)
    if not model or action not in {"list", "create", "update", "delete"}:
        raise HTTPException(status_code=400, detail="Unsupported resource or action")
    if resource == "links" and action == "create":
        payload = ProfileLinkCreate.model_validate(payload).model_dump()
        payload["normalized_name"] = payload["name"].strip().lower()
        payload["normalized_url"] = payload["url"].strip().lower().rstrip("/")
        duplicate = db.scalar(select(ProfileLink).where(ProfileLink.normalized_name == payload["normalized_name"], ProfileLink.normalized_url == payload["normalized_url"]))
        if duplicate:
            for key, value in payload.items():
                setattr(duplicate, key, value)
            db.commit()
            return {"status": "upserted", "resource": resource, "id": str(duplicate.id)}
    elif resource == "repositories" and action == "create":
        if not payload.get("name") and payload.get("url"):
            payload["name"] = payload["url"].rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
        if not payload.get("name"):
            raise HTTPException(status_code=422, detail="Repository name or URL is required")
        if payload.get("url") and db.scalar(select(Repository).where(Repository.url == payload["url"])):
            duplicate = db.scalar(select(Repository).where(Repository.url == payload["url"]))
            for key, value in payload.items():
                setattr(duplicate, key, value)
            db.commit()
            return {"status": "upserted", "resource": resource, "id": str(duplicate.id)}
    elif resource == "technologies" and action == "create":
        if not payload.get("name"):
            raise HTTPException(status_code=422, detail="Technology name is required")
        duplicate = db.scalar(select(Technology).where(func.lower(Technology.name) == payload["name"].strip().lower()))
        if duplicate:
            for key, value in payload.items():
                if key != "id" and hasattr(duplicate, key):
                    setattr(duplicate, key, value)
            db.commit()
            return {"status": "upserted", "resource": resource, "id": str(duplicate.id)}
    elif resource == "role-policies" and action == "create":
        role_family = str(payload.get("role_family") or "").strip().lower()
        if not role_family:
            raise HTTPException(status_code=422, detail="Role policy requires a role_family")
        payload["role_family"] = role_family
        duplicate = db.scalar(select(RolePolicy).where(RolePolicy.role_family == role_family))
        if duplicate:
            for key, value in payload.items():
                if key != "id" and hasattr(duplicate, key):
                    setattr(duplicate, key, value)
            db.commit()
            return {"status": "upserted", "resource": resource, "id": str(duplicate.id)}
    elif resource == "entry-assets" and action == "create":
        required = {"entry_id", "asset_id", "role"}
        if not required.issubset(payload):
            raise HTTPException(status_code=422, detail="entry-assets requires entry_id, asset_id, and role")
        duplicate = db.scalar(select(EntryAsset).where(EntryAsset.entry_id == payload["entry_id"], EntryAsset.asset_id == payload["asset_id"], EntryAsset.role == payload["role"]))
        if duplicate:
            for key, value in payload.items():
                if key != "id" and hasattr(duplicate, key):
                    setattr(duplicate, key, value)
            db.commit()
            return {"status": "upserted", "resource": resource, "id": str(duplicate.id)}
    elif resource == "entry-technologies" and action == "create":
        required = {"entry_id", "technology_id"}
        if not required.issubset(payload):
            raise HTTPException(status_code=422, detail="entry-technologies requires entry_id and technology_id")
        duplicate = db.scalar(select(EntryTechnology).where(EntryTechnology.entry_id == payload["entry_id"], EntryTechnology.technology_id == payload["technology_id"]))
        if duplicate:
            return {"status": "upserted", "resource": resource}
    elif resource in {"topology", "metrics", "decisions", "highlights", "quotes", "snippets", "documents", "badges"} and action == "create":
        if not payload.get("entry_id"):
            raise HTTPException(status_code=422, detail=f"{resource} requires an entry_id")
    elif resource == "links" and action == "update":
        identity = payload.get("id")
        if not identity:
            raise HTTPException(status_code=422, detail="Link updates require an id")
        payload = ProfileLinkUpdate.model_validate({key: value for key, value in payload.items() if key != "id"}).model_dump(exclude_unset=True) | {"id": identity}
        existing = db.get(ProfileLink, identity)
        if not existing:
            raise HTTPException(status_code=404, detail="Content not found")
        name = payload.get("name", existing.name).strip().lower()
        url = payload.get("url", existing.url).strip().lower().rstrip("/")
        duplicate = db.scalar(select(ProfileLink).where(ProfileLink.id != identity, ProfileLink.normalized_name == name, ProfileLink.normalized_url == url))
        if duplicate:
            raise HTTPException(status_code=409, detail=f"A profile link with this name and URL already exists: {duplicate.id}")
        payload["normalized_name"] = name
        payload["normalized_url"] = url
    if action == "list":
        query = select(model)
        if resource == "entry-assets" and payload.get("entry_id"):
            query = query.where(EntryAsset.entry_id == payload["entry_id"])
        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        page = max(int(payload.get("page", 1)), 1)
        page_size = max(min(int(payload.get("page_size", 100)), 500), 1)
        records = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
        response.headers["X-Total-Count"] = str(total)
        response.headers["X-Returned-Count"] = str(len(records))
        response.headers["X-Page"] = str(page)
        response.headers["X-Page-Size"] = str(page_size)
        return [model_record(item) for item in records]
    identity = payload.get("id") or payload.get("key")
    item = db.get(model, identity) if identity else None
    if action == "delete":
        if not item:
            raise HTTPException(status_code=404, detail="Content not found")
        db.delete(item)
    elif action == "update":
        if not item:
            raise HTTPException(status_code=404, detail="Content not found")
        for key, value in payload.items():
            if key not in {"id", "key"} and hasattr(item, key):
                setattr(item, key, value)
    else:
        if model is Entry and payload.get("slug") and db.scalar(select(Entry).where(Entry.slug == payload["slug"])):
            raise HTTPException(status_code=409, detail=f"An entry with slug '{payload['slug']}' already exists; use update instead")
        db.add(model(**{key: value for key, value in payload.items() if hasattr(model, key)}))
    db.commit()
    return {"status": action, "resource": resource}


@router.post("/admin/content/bulk", dependencies=[Depends(require_service_key)])
def bulk_manage_links(request: BulkLinkMutation, db: Session = Depends(get_db)):
    """Validate and apply contact-link mutations atomically."""
    prepared = []
    for operation in request.operations:
        payload = dict(operation.payload)
        if operation.action == "create":
            data = ProfileLinkCreate.model_validate(payload).model_dump()
            data["normalized_name"] = data["name"].strip().lower()
            data["normalized_url"] = data["url"].strip().lower().rstrip("/")
            prepared.append((operation, data, None))
        elif operation.action == "update":
            if not operation.id:
                raise HTTPException(status_code=422, detail="Link updates require an id")
            item = db.get(ProfileLink, operation.id)
            if not item:
                raise HTTPException(status_code=404, detail=f"Link not found: {operation.id}")
            data = ProfileLinkUpdate.model_validate(payload).model_dump(exclude_unset=True)
            name = data.get("name", item.name).strip().lower()
            url = data.get("url", item.url).strip().lower().rstrip("/")
            data.update(normalized_name=name, normalized_url=url)
            prepared.append((operation, data, item))
        else:
            if not operation.id:
                raise HTTPException(status_code=422, detail="Link deletes require an id")
            item = db.get(ProfileLink, operation.id)
            if not item:
                raise HTTPException(status_code=404, detail=f"Link not found: {operation.id}")
            prepared.append((operation, {}, item))
    identities = [(data.get("normalized_name"), data.get("normalized_url")) for _, data, _ in prepared if data]
    if len(identities) != len(set(identities)):
        raise HTTPException(status_code=409, detail="Bulk request contains duplicate link identities")
    for operation, data, item in prepared:
        if operation.action == "create":
            duplicate = db.scalar(select(ProfileLink).where(ProfileLink.normalized_name == data["normalized_name"], ProfileLink.normalized_url == data["normalized_url"]))
            if duplicate:
                # Link creation is intentionally idempotent. Re-adding the same
                # identity updates its supplied metadata instead of failing.
                for key, value in data.items():
                    setattr(duplicate, key, value)
            else:
                db.add(ProfileLink(**data))
        elif operation.action == "update":
            duplicate = db.scalar(select(ProfileLink).where(ProfileLink.id != item.id, ProfileLink.normalized_name == data["normalized_name"], ProfileLink.normalized_url == data["normalized_url"]))
            if duplicate:
                raise HTTPException(status_code=409, detail=f"Profile link already exists: {duplicate.id}")
            for key, value in data.items():
                setattr(item, key, value)
        else:
            db.delete(item)
    db.commit()
    return {"status": "applied", "resource": "links", "count": len(prepared)}


@router.get("/admin/search", dependencies=[Depends(require_service_key)])
def admin_search(q: str = Query(min_length=1), db: Session = Depends(get_db)):
    from ..services.search import admin_search as search_all
    return search_all(db, q)


@router.post("/entries", response_model=EntryRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_service_key)])
def create_entry(payload: EntryCreate, db: Session = Depends(get_db)):
    entry = Entry(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.patch("/entries/{entry_id}", response_model=EntryRead, dependencies=[Depends(require_service_key)])
def update_entry(entry_id: UUID, payload: EntryUpdate, db: Session = Depends(get_db)):
    entry = db.get(Entry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_service_key)])
def delete_entry(entry_id: UUID, db: Session = Depends(get_db)):
    entry = db.get(Entry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()


@router.patch("/entries/slug/{slug}", response_model=EntryRead, dependencies=[Depends(require_service_key)])
def update_entry_by_slug(slug: str, payload: EntryUpdate, db: Session = Depends(get_db)):
    entry = db.scalar(select(Entry).where(Entry.slug == slug))
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/entries/slug/{slug}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_service_key)])
def delete_entry_by_slug(slug: str, db: Session = Depends(get_db)):
    entry = db.scalar(select(Entry).where(Entry.slug == slug))
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
