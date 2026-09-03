from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Response, UploadFile, status
import boto3
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import cast, func, or_, select, String
from sqlalchemy.orm import Session
from uuid import UUID
import re

from .auth import require_service_key
from .db import get_db
from .models import BucketListItem, Certificate, Education, Entry, Profile, ProfileLink, SiteAsset, SkillGroup, SiteSetting
from .schemas import EntryCreate, EntryRead, EntryUpdate

app = FastAPI(title="mikesplore portfolio API", version="1.0.0")
from .config import settings
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["*"])


def slugify(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")[:100]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/counts")
def content_counts(db: Session = Depends(get_db)):
    return {
        "projects": len(db.scalars(select(Entry).where(Entry.content_type == "project", Entry.is_visible.is_(True))).all()),
        "hackathons": len(db.scalars(select(Entry).where(Entry.content_type == "hackathon", Entry.is_visible.is_(True))).all()),
        "events": len(db.scalars(select(Entry).where(Entry.content_type == "event", Entry.is_visible.is_(True))).all()),
        "certificates": len(db.scalars(select(Certificate).where(Certificate.is_visible.is_(True))).all()),
        "bucket_list": len(db.scalars(select(BucketListItem)).all()),
    }


@app.get("/profile")
def get_profile(db: Session = Depends(get_db)):
    profile = db.get(Profile, 1)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {key: getattr(profile, key) for key in ("name", "tagline", "location", "focus", "experience", "availability_status", "availability_detail", "about")}


@app.patch("/profile", response_model=dict, dependencies=[Depends(require_service_key)])
def update_profile(payload: dict, db: Session = Depends(get_db)):
    profile = db.get(Profile, 1)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    allowed = {"name", "tagline", "location", "focus", "experience", "availability_status", "availability_detail", "about"}
    for key, value in payload.items():
        if key in allowed:
            setattr(profile, key, value)
    db.commit(); db.refresh(profile)
    return {key: getattr(profile, key) for key in allowed}


@app.post("/admin/content", dependencies=[Depends(require_service_key)])
def manage_content(resource: str, action: str, payload: dict, db: Session = Depends(get_db)):
    models = {"entries": Entry, "certificates": Certificate, "assets": SiteAsset, "links": ProfileLink, "skills": SkillGroup, "education": Education, "bucket-list": BucketListItem, "settings": SiteSetting}
    model = models.get(resource)
    if not model or action not in {"list", "create", "update", "delete"}:
        raise HTTPException(status_code=400, detail="Unsupported resource or action")
    if action == "list":
        return [{column.name: getattr(item, column.name) for column in model.__table__.columns}
                for item in db.scalars(select(model)).all()]
    identity = payload.get("id") or payload.get("key")
    item = db.get(model, identity) if identity else None
    if action == "delete":
        if not item: raise HTTPException(status_code=404, detail="Content not found")
        db.delete(item)
    elif action == "update":
        if not item: raise HTTPException(status_code=404, detail="Content not found")
        for key, value in payload.items():
            if key not in {"id", "key"} and hasattr(item, key): setattr(item, key, value)
    else:
        db.add(model(**{key: value for key, value in payload.items() if hasattr(model, key)}))
    db.commit()
    return {"status": action, "resource": resource}


@app.get("/admin/search", dependencies=[Depends(require_service_key)])
def admin_search(q: str = Query(min_length=1), db: Session = Depends(get_db)):
    models = {"entries": Entry, "certificates": Certificate, "assets": SiteAsset, "links": ProfileLink, "skills": SkillGroup, "education": Education, "bucket-list": BucketListItem, "settings": SiteSetting}
    terms = [term.lower() for term in re.findall(r"[a-z0-9]+", q.lower()) if len(term) > 2]
    results = []
    for resource, model in models.items():
        for item in db.scalars(select(model)).all():
            values = {column.name: getattr(item, column.name) for column in model.__table__.columns}
            haystack = " ".join(str(value).lower() for value in values.values())
            score = sum(term in haystack for term in terms)
            if score:
                results.append({"resource": resource, "score": score, "record": values})
    return sorted(results, key=lambda result: result["score"], reverse=True)[:10]


@app.get("/certificates")
def list_certificates(db: Session = Depends(get_db)):
    return db.scalars(select(Certificate).where(Certificate.is_visible.is_(True)).order_by(Certificate.custom_order)).all()


@app.delete("/certificates/{certificate_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_service_key)])
def delete_certificate(certificate_id: UUID, db: Session = Depends(get_db)):
    certificate = db.get(Certificate, certificate_id)
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")
    db.delete(certificate)
    db.commit()


@app.post("/certificates", response_model=dict, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_service_key)])
def upload_certificate(title: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    from .config import settings
    if not all((settings.r2_endpoint_url, settings.r2_access_key_id, settings.r2_secret_access_key, settings.r2_bucket_name, settings.r2_public_base_url)):
        raise HTTPException(status_code=503, detail="R2 storage is not configured")
    object_key = f"certificates/{slugify(title)}-{file.filename}"
    client = boto3.client("s3", endpoint_url=settings.r2_endpoint_url, aws_access_key_id=settings.r2_access_key_id, aws_secret_access_key=settings.r2_secret_access_key, region_name="auto")
    client.upload_fileobj(file.file, settings.r2_bucket_name, object_key, ExtraArgs={"ContentType": file.content_type or "application/octet-stream"})
    item = Certificate(title=title, image_url=f"{settings.r2_public_base_url.rstrip('/')}/{object_key}", custom_order=0)
    db.add(item); db.commit(); db.refresh(item)
    return {"id": str(item.id), "title": item.title, "image_url": item.image_url}


@app.get("/profile/links")
def list_profile_links(db: Session = Depends(get_db)):
    return db.scalars(select(ProfileLink).where(ProfileLink.is_visible.is_(True)).order_by(ProfileLink.custom_order)).all()


@app.get("/education")
def list_education(db: Session = Depends(get_db)):
    return db.scalars(select(Education).order_by(Education.custom_order)).all()


@app.get("/skills")
def list_skills(db: Session = Depends(get_db)):
    return db.scalars(select(SkillGroup).where(SkillGroup.is_visible.is_(True)).order_by(SkillGroup.custom_order)).all()


@app.get("/bucket-list")
def list_bucket_list(db: Session = Depends(get_db)):
    return db.scalars(select(BucketListItem).order_by(BucketListItem.custom_order)).all()


@app.get("/assets")
def list_assets(db: Session = Depends(get_db)):
    return [{"id": asset.id, "asset_type": asset.asset_type, "url": asset.url, "label": asset.label} for asset in db.scalars(select(SiteAsset)).all()]


@app.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_service_key)])
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(SiteAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(asset)
    db.commit()


@app.post("/assets", response_model=dict, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_service_key)])
def upload_asset(asset_type: str = Form(...), label: str = Form(""), file: UploadFile = File(...), db: Session = Depends(get_db)):
    from .config import settings
    if not all((settings.r2_endpoint_url, settings.r2_access_key_id, settings.r2_secret_access_key, settings.r2_bucket_name, settings.r2_public_base_url)):
        raise HTTPException(status_code=503, detail="R2 storage is not configured")
    object_key = f"assets/{slugify(asset_type)}/{slugify(label or file.filename or 'upload')}-{file.filename}"
    client = boto3.client("s3", endpoint_url=settings.r2_endpoint_url, aws_access_key_id=settings.r2_access_key_id, aws_secret_access_key=settings.r2_secret_access_key, region_name="auto")
    client.upload_fileobj(file.file, settings.r2_bucket_name, object_key, ExtraArgs={"ContentType": file.content_type or "application/octet-stream"})
    asset_url = f"{settings.r2_public_base_url.rstrip('/')}/{object_key}"
    item = None
    previous_url = None
    if asset_type == "profile-image":
        item = db.scalar(select(SiteAsset).where(SiteAsset.asset_type == "profile-image"))
    if item:
        previous_url = item.url
        item.label, item.url = label or file.filename, asset_url
    else:
        item = SiteAsset(asset_type=asset_type, label=label or file.filename, url=asset_url)
        db.add(item)
    db.commit(); db.refresh(item)
    if previous_url and previous_url.startswith(settings.r2_public_base_url.rstrip("/") + "/"):
        previous_key = previous_url.removeprefix(settings.r2_public_base_url.rstrip("/") + "/")
        if previous_key != object_key:
            try:
                client.delete_object(Bucket=settings.r2_bucket_name, Key=previous_key)
            except Exception:
                pass
    return {"id": item.id, "asset_type": item.asset_type, "label": item.label, "url": item.url}


@app.get("/settings/{key}")
def get_setting(key: str, db: Session = Depends(get_db)):
    setting = db.get(SiteSetting, key)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting.value


@app.get("/search")
def search_portfolio(q: str = Query(min_length=1), page: int = Query(default=1, ge=1), page_size: int = Query(default=5, ge=1, le=50), db: Session = Depends(get_db)):
    term = f"%{q}%"
    query = select(Entry).where(Entry.is_visible.is_(True), or_(Entry.title.ilike(term), Entry.blurb.ilike(term), cast(Entry.tags, String).ilike(term), cast(Entry.links, String).ilike(term))).order_by(Entry.custom_order, Entry.date.desc().nullslast())
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    entries = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    profile = db.get(Profile, 1) if any(word in q.lower() for word in ("who", "michael", "person", "about", "background")) else None
    profile_data = None if not profile else {key: getattr(profile, key) for key in ("name", "tagline", "location", "focus", "experience", "availability_status", "availability_detail", "about")}
    certificate_query = select(Certificate).where(Certificate.is_visible.is_(True), Certificate.title.ilike(term))
    certificates = db.scalars(certificate_query).all()
    skill_groups = db.scalars(select(SkillGroup).where(SkillGroup.is_visible.is_(True))).all()
    skills = [{"category": item.category, "skills": [skill for skill in item.skills if any(word in str(skill).lower() for word in terms) or any(word in item.category.lower() for word in terms)]} for item in skill_groups]
    skills = [item for item in skills if item["skills"]]
    links = db.scalars(select(ProfileLink).where(ProfileLink.is_visible.is_(True))).all()
    matching_links = [item for item in links if any(word in f"{item.name} {item.label or ''} {item.handle or ''}".lower() for word in terms)]
    education = db.scalars(select(Education)).all()
    matching_education = [item for item in education if any(word in f"{item.degree} {item.school} {item.location or ''}".lower() for word in terms)]
    bucket_items = db.scalars(select(BucketListItem)).all()
    matching_bucket = [item for item in bucket_items if any(word in f"{item.title} {item.remark or ''}".lower() for word in terms)]
    return {"profile": profile_data, "entries": entries, "certificates": certificates, "skills": skills, "links": matching_links, "education": matching_education, "bucket_list": matching_bucket, "total": total + len(certificates) + len(skills) + len(matching_links) + len(matching_education) + len(matching_bucket), "page": page, "page_size": page_size}


@app.get("/entries", response_model=list[EntryRead])
def list_entries(
    response: Response,
    content_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = select(Entry).where(Entry.is_visible.is_(True)).order_by(Entry.custom_order, Entry.date.desc().nullslast())
    if content_type:
        query = query.where(Entry.content_type == content_type)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    response.headers["X-Total-Count"] = str(total)
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
