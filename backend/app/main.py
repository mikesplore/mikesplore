from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Response, UploadFile, status
import boto3
from io import BytesIO
from pathlib import Path
import tempfile
from pypdf import PdfReader
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import cast, func, or_, select, String
from sqlalchemy.orm import Session
from uuid import UUID, uuid4
import re
import httpx
import json
import hashlib
from datetime import date as date_value

from .auth import require_service_key
from .db import get_db
from .models import BucketListItem, Certificate, CvVersion, Education, Entry, Profile, ProfileLink, SiteAsset, SkillGroup, SiteSetting
from .schemas import EntryCreate, EntryRead, EntryUpdate

app = FastAPI(title="Portfolio API", version="1.0.0")
from .config import settings
frontend_origins = [origin.strip().rstrip("/") for origin in settings.frontend_origin.split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=frontend_origins, allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["*"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
PUBLIC_SETTING_KEYS = {"public_notice"}


def _source_entry(source: str, item: dict, visible: bool) -> dict:
    if source == "devto":
        url = item.get("url") or item.get("canonical_url")
        title = item.get("title", "Untitled article")
        return {"slug": slugify(title), "content_type": "article", "title": title,
                "blurb": item.get("description") or item.get("description_markdown") or "",
                "date": (item.get("published_at") or item.get("created_at", ""))[:10] or None,
                "is_visible": True, "tags": item.get("tag_list", []),
                "details": {"readTime": item.get("reading_time_minutes")},
                "links": {"url": url}, "media": {"thumbnail": item.get("cover_image") or item.get("social_image")},
                "source": {"provider": "dev.to", "key": url}}
    url = item.get("html_url")
    title = item.get("name", "Untitled repository")
    return {"slug": slugify(title), "content_type": "project", "title": title,
            "blurb": item.get("description") or "", "date": (item.get("created_at", ""))[:10] or None,
            "is_visible": visible, "tech_stack": [item["language"]] if item.get("language") else [],
            "tags": [], "details": {"stars": item.get("stargazers_count", 0), "fork": item.get("fork", False)},
            "links": {"url": url, "repo": url}, "media": {"thumbnail": (item.get("owner") or {}).get("avatar_url")},
            "source": {"provider": "github", "key": url, "repo": item.get("full_name")}}


async def _fetch_source(source: str) -> list[dict]:
    if source not in {"devto", "github"}:
        raise HTTPException(status_code=400, detail="Source must be devto or github")
    username = settings.devto_username if source == "devto" else settings.github_username
    if not username:
        raise HTTPException(status_code=503, detail=f"{source} username is not configured")
    url = (f"https://dev.to/api/articles?username={settings.devto_username}&per_page=100" if source == "devto"
           else f"https://api.github.com/users/{settings.github_username}/repos?per_page=100&sort=updated")
    headers = {"Accept": "application/vnd.github+json"}
    if source == "github" and settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


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
        if model is Entry and payload.get("slug") and db.scalar(select(Entry).where(Entry.slug == payload["slug"])):
            raise HTTPException(status_code=409, detail=f"An entry with slug '{payload['slug']}' already exists; use update instead")
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


@app.get("/admin/sync/{source}", dependencies=[Depends(require_service_key)])
async def preview_sync(source: str):
    """Fetch source data without changing the database; the bot shows this result for approval."""
    try:
        items = await _fetch_source(source)
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"{source} fetch failed: {error}")
    return {"source": source, "items": [_source_entry(source, item, source == "devto") for item in items]}


@app.post("/admin/sync/{source}", dependencies=[Depends(require_service_key)])
def apply_sync(source: str, payload: dict, db: Session = Depends(get_db)):
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
            entry = Entry(**data)
            db.add(entry)
        else:
            # Imported fields may refresh, but editorial fields and GitHub selection survive.
            old_visible = entry.is_visible
            for field in ("title", "blurb", "date", "tech_stack", "tags", "details", "links", "media", "source"):
                setattr(entry, field, data[field])
            entry.is_visible = old_visible if source == "github" and key not in selected else (key in selected if source == "github" else True)
        if source == "github" and key in selected:
            entry.is_visible = True
        changed.append({"title": data.get("title"), "key": key, "visible": entry.is_visible})
    db.commit()
    return {"source": source, "updated": len(changed), "items": changed}


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
    object_key = f"certificates/{slugify(title)}-{uuid4().hex}-{file.filename}"
    client = boto3.client("s3", endpoint_url=settings.r2_endpoint_url, aws_access_key_id=settings.r2_access_key_id, aws_secret_access_key=settings.r2_secret_access_key, region_name="auto")
    file_bytes = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Certificate file exceeds the 10 MB limit")
    client.upload_fileobj(BytesIO(file_bytes), settings.r2_bucket_name, object_key, ExtraArgs={"ContentType": file.content_type or "application/octet-stream"})
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
async def upload_asset(asset_type: str = Form(...), label: str = Form(""), file: UploadFile = File(...), db: Session = Depends(get_db)):
    from .config import settings
    if not all((settings.r2_endpoint_url, settings.r2_access_key_id, settings.r2_secret_access_key, settings.r2_bucket_name, settings.r2_public_base_url)):
        raise HTTPException(status_code=503, detail="R2 storage is not configured")
    object_key = f"assets/{slugify(asset_type)}/{slugify(label or file.filename or 'upload')}-{uuid4().hex}-{file.filename}"
    client = boto3.client("s3", endpoint_url=settings.r2_endpoint_url, aws_access_key_id=settings.r2_access_key_id, aws_secret_access_key=settings.r2_secret_access_key, region_name="auto")
    file_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Upload exceeds the 10 MB limit")
    cv_text = None
    if asset_type == "cv":
        try:
            cv_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(file_bytes)).pages).strip()
        except Exception:
            raise HTTPException(status_code=400, detail="The CV must be a readable PDF file")
    client.upload_fileobj(BytesIO(file_bytes), settings.r2_bucket_name, object_key, ExtraArgs={"ContentType": file.content_type or "application/octet-stream"})
    asset_url = f"{settings.r2_public_base_url.rstrip('/')}/{object_key}"
    item = None
    previous_url = None
    if asset_type in {"profile-image", "cv"}:
        item = db.scalar(select(SiteAsset).where(SiteAsset.asset_type == asset_type))
    if item:
        previous_url = item.url
        item.label, item.url = label or file.filename, asset_url
    else:
        item = SiteAsset(asset_type=asset_type, label=label or file.filename, url=asset_url)
        db.add(item)
    db.commit(); db.refresh(item)
    if asset_type == "cv":
        cv_setting = db.get(SiteSetting, "cv_text")
        if cv_setting:
            cv_setting.value = {"text": cv_text, "asset_url": asset_url}
        else:
            db.add(SiteSetting(key="cv_text", value={"text": cv_text, "asset_url": asset_url}))
        db.commit()
    if previous_url and previous_url.startswith(settings.r2_public_base_url.rstrip("/") + "/"):
        previous_key = previous_url.removeprefix(settings.r2_public_base_url.rstrip("/") + "/")
        if previous_key != object_key:
            try:
                client.delete_object(Bucket=settings.r2_bucket_name, Key=previous_key)
            except Exception:
                pass
    return {"id": item.id, "asset_type": item.asset_type, "label": item.label, "url": item.url}


def _validate_cv_data(data: dict) -> dict:
    required = {"name", "title", "contact", "summary", "skills", "projects", "certifications", "education"}
    if not isinstance(data, dict) or not required.issubset(data):
        raise HTTPException(status_code=422, detail=f"CV JSON must contain: {', '.join(sorted(required))}")
    if not isinstance(data["contact"], dict) or not isinstance(data["summary"], str):
        raise HTTPException(status_code=422, detail="CV contact must be an object and summary must be text")
    if not isinstance(data["skills"], list) or not isinstance(data["projects"], list) or not isinstance(data["education"], list):
        raise HTTPException(status_code=422, detail="CV skills, projects, and education must be arrays")
    if any(not isinstance(group, dict) or not isinstance(group.get("category"), str) or not isinstance(group.get("items"), list) for group in data["skills"]):
        raise HTTPException(status_code=422, detail="Each CV skill group needs category and items")
    if any(not isinstance(project, dict) or not all(key in project for key in ("name", "date", "stack", "bullets")) or not isinstance(project["bullets"], list) for project in data["projects"]):
        raise HTTPException(status_code=422, detail="Each CV project needs name, date, stack, and bullets")
    if any(not isinstance(item, str) for item in data["certifications"]):
        raise HTTPException(status_code=422, detail="CV certifications must be text values")
    if any(not isinstance(item, dict) or not all(key in item for key in ("institution", "degree")) for item in data["education"]):
        raise HTTPException(status_code=422, detail="Each CV education item needs institution and degree")
    return data


def _cv_base_hash(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _project_id(project: dict) -> str:
    return slugify(project.get("name", ""))


def _validate_cv_patch(patch: dict) -> dict:
    allowed = {"summary", "selected_projects", "selected_skills"}
    if not isinstance(patch, dict) or set(patch) != allowed:
        raise HTTPException(status_code=422, detail="CV patch must contain exactly summary, selected_projects, and selected_skills")
    summary = patch["summary"]
    if not isinstance(summary, dict) or set(summary) != {"old", "new"} or not all(isinstance(summary[key], str) for key in summary):
        raise HTTPException(status_code=422, detail="CV summary patch must contain old and new text")
    if not isinstance(patch["selected_projects"], list) or not all(isinstance(item, str) for item in patch["selected_projects"]):
        raise HTTPException(status_code=422, detail="selected_projects must be a list of stable IDs")
    if not isinstance(patch["selected_skills"], dict) or any(not isinstance(value, list) or not all(isinstance(item, str) for item in value) for value in patch["selected_skills"].values()):
        raise HTTPException(status_code=422, detail="selected_skills must map categories to skill names")
    if not patch["selected_projects"] or not any(patch["selected_skills"].values()):
        raise HTTPException(status_code=422, detail="The job must match at least one verified project and skill")
    return patch


def _apply_cv_patch(base: dict, patch: dict) -> dict:
    _validate_cv_data(base)
    _validate_cv_patch(patch)
    projects = { _project_id(project): project for project in base["projects"] }
    unknown_projects = set(patch["selected_projects"]) - set(projects)
    if unknown_projects:
        raise HTTPException(status_code=422, detail=f"Unknown project IDs: {', '.join(sorted(unknown_projects))}")
    skills = {group["category"]: set(group["items"]) for group in base["skills"]}
    for category, selected in patch["selected_skills"].items():
        if category not in skills or not set(selected).issubset(skills[category]):
            raise HTTPException(status_code=422, detail=f"Unknown skills in category: {category}")
    tailored = dict(base)
    tailored["summary"] = patch["summary"]["new"]
    tailored["projects"] = [projects[project_id] for project_id in patch["selected_projects"]]
    tailored["skills"] = [{"category": category, "items": selected} for category, selected in patch["selected_skills"].items()]
    return tailored


@app.get("/admin/cv/base", dependencies=[Depends(require_service_key)])
def get_cv_base(db: Session = Depends(get_db)):
    setting = db.get(SiteSetting, "cv_data")
    if not setting:
        raise HTTPException(status_code=404, detail="Base CV JSON has not been configured")
    return {"data": setting.value, "revision": _cv_base_hash(setting.value)}


@app.get("/admin/cv/profile", dependencies=[Depends(require_service_key)])
def get_cv_profile(db: Session = Depends(get_db)):
    setting = db.get(SiteSetting, "cv_data")
    if not setting:
        raise HTTPException(status_code=404, detail="Base CV JSON has not been configured")
    data = setting.value
    return {"name": data.get("name"), "title": data.get("title"), "contact": data.get("contact"), "summary": data.get("summary"), "revision": _cv_base_hash(data)}


@app.get("/admin/cv/projects", dependencies=[Depends(require_service_key)])
def search_cv_projects(q: str = Query(default=""), db: Session = Depends(get_db)):
    setting = db.get(SiteSetting, "cv_data")
    if not setting:
        raise HTTPException(status_code=404, detail="Base CV JSON has not been configured")
    term = q.lower().strip()
    results = []
    for project in setting.value.get("projects", []):
        haystack = json.dumps(project).lower()
        if not term or term in haystack:
            results.append({"id": _project_id(project), "name": project["name"], "date": project.get("date"), "stack": project.get("stack"), "bullets": project.get("bullets", [])})
    return results


@app.get("/admin/cv/skills", dependencies=[Depends(require_service_key)])
def search_cv_skills(q: str = Query(default=""), db: Session = Depends(get_db)):
    setting = db.get(SiteSetting, "cv_data")
    if not setting:
        raise HTTPException(status_code=404, detail="Base CV JSON has not been configured")
    term = q.lower().strip()
    return [{"category": group["category"], "items": [item for item in group["items"] if not term or term in item.lower() or term in group["category"].lower()]}
            for group in setting.value.get("skills", [])]


@app.post("/admin/cv/base", dependencies=[Depends(require_service_key)])
def save_cv_base(payload: dict, db: Session = Depends(get_db)):
    data = _validate_cv_data(payload)
    setting = db.get(SiteSetting, "cv_data")
    if setting:
        setting.value = data
    else:
        db.add(SiteSetting(key="cv_data", value=data))
    db.commit()
    return {"status": "saved"}


@app.post("/admin/cv/render", dependencies=[Depends(require_service_key)])
def render_cv_version(payload: dict, db: Session = Depends(get_db)):
    setting = db.get(SiteSetting, "cv_data")
    if not setting:
        raise HTTPException(status_code=404, detail="Base CV JSON has not been configured")
    base = setting.value
    if payload.get("base_revision") != _cv_base_hash(base):
        raise HTTPException(status_code=409, detail="The base CV changed while this patch was pending; run /apply again")
    patch = _validate_cv_patch(payload.get("patch") or {})
    data = _apply_cv_patch(base, patch)
    job_description = str(payload.get("job_description") or "").strip()
    label = str(payload.get("label") or "Tailored CV")[:255]
    if not job_description:
        raise HTTPException(status_code=422, detail="job_description is required")
    from .cv_renderer import render
    from .config import settings
    if not all((settings.r2_endpoint_url, settings.r2_access_key_id, settings.r2_secret_access_key, settings.r2_bucket_name, settings.r2_public_base_url)):
        raise HTTPException(status_code=503, detail="R2 storage is not configured")
    version_id = uuid4()
    with tempfile.TemporaryDirectory() as directory:
        output_path = Path(directory) / "cv.pdf"
        render(data, str(output_path))
        pdf_bytes = output_path.read_bytes()
    object_key = f"cv-versions/{version_id}.pdf"
    client = boto3.client("s3", endpoint_url=settings.r2_endpoint_url, aws_access_key_id=settings.r2_access_key_id, aws_secret_access_key=settings.r2_secret_access_key, region_name="auto")
    client.upload_fileobj(BytesIO(pdf_bytes), settings.r2_bucket_name, object_key, ExtraArgs={"ContentType": "application/pdf"})
    pdf_url = f"{settings.r2_public_base_url.rstrip('/')}/{object_key}"
    db.add(CvVersion(id=version_id, label=label, job_description=job_description, data=data, patch=patch, base_snapshot=base, pdf_url=pdf_url))
    db.commit()
    return {"id": str(version_id), "label": label, "pdf_url": pdf_url}


@app.get("/cv/search")
def search_cv(q: str = Query(min_length=1), db: Session = Depends(get_db)):
    setting = db.get(SiteSetting, "cv_text")
    if not setting:
        return {"matches": [], "total": 0}
    text = setting.value.get("text", "")
    terms = [word.lower() for word in re.findall(r"[a-z0-9]+", q.lower()) if len(word) > 2]
    if not terms or not all(term in text.lower() for term in terms):
        return {"matches": [], "total": 0}
    lower = text.lower()
    position = min(lower.find(term) for term in terms if term in lower)
    return {"matches": [text[max(0, position - 250):position + 750]], "total": 1}


@app.get("/settings/{key}")
def get_setting(key: str, db: Session = Depends(get_db)):
    if key not in PUBLIC_SETTING_KEYS:
        raise HTTPException(status_code=404, detail="Setting not found")
    setting = db.get(SiteSetting, key)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting.value


@app.get("/search")
def search_portfolio(q: str = Query(min_length=1), page: int = Query(default=1, ge=1), page_size: int = Query(default=5, ge=1, le=50), db: Session = Depends(get_db)):
    term = f"%{q}%"
    terms = [word.lower() for word in re.findall(r"[a-z0-9]+", q.lower()) if len(word) > 2]
    query = select(Entry).where(Entry.is_visible.is_(True), or_(Entry.title.ilike(term), Entry.blurb.ilike(term), cast(Entry.tags, String).ilike(term), cast(Entry.links, String).ilike(term))).order_by(Entry.custom_order, Entry.date.desc().nullslast())
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    entries = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    stored_profile = db.get(Profile, 1)
    owner_name = (stored_profile.name or "").lower() if stored_profile else ""
    profile = stored_profile if any(word in q.lower() for word in ("who", "person", "about", "background")) or (owner_name and owner_name in q.lower()) else None
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

@app.get("/entries/slug/{slug}", response_model=EntryRead)
def get_entry_by_slug(slug: str, db: Session = Depends(get_db)):
    entry = db.scalar(select(Entry).where(Entry.slug == slug, Entry.is_visible.is_(True)))
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry

@app.patch("/entries/slug/{slug}", response_model=EntryRead, dependencies=[Depends(require_service_key)])
def update_entry_by_slug(slug: str, payload: EntryUpdate, db: Session = Depends(get_db)):
    entry = db.scalar(select(Entry).where(Entry.slug == slug))
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit(); db.refresh(entry)
    return entry

@app.delete("/entries/slug/{slug}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_service_key)])
def delete_entry_by_slug(slug: str, db: Session = Depends(get_db)):
    entry = db.scalar(select(Entry).where(Entry.slug == slug))
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()


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


# Host the Telegram webhook in the same Render service as the portfolio API.
# This keeps one always-on instance while preserving /telegram/webhook.
from bot.app.main import app as telegram_app
app.mount("/", telegram_app)
