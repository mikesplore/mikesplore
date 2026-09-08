from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import require_service_key
from .config import settings
from .db import get_db
from .models import BucketListItem, Certificate, Education, Entry, LLMUsage, Profile, ProfileLink, SkillGroup, SiteSetting
from .routers import admin_content, admin_sync, assets, cv as cv_router, public_projects
from .routers.assets import MAX_UPLOAD_BYTES  # noqa: F401  (kept so tests/tooling can import it from app.main)
from .schemas import EntryRead, ProfileUpdate
from .services import cv as cv_service
from .services.search import search_portfolio as search_portfolio_service

app = FastAPI(title="Portfolio API", version="1.0.0")

frontend_origins = [origin.strip().rstrip("/") for origin in settings.frontend_origin.split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=frontend_origins, allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["*"])

PUBLIC_SETTING_KEYS = {"public_notice"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/internal/llm-usage", dependencies=[Depends(require_service_key)])
def record_llm_usage(payload: dict, db: Session = Depends(get_db)):
    allowed = {"provider", "model", "workflow", "request_id", "input_tokens", "cached_input_tokens", "output_tokens", "total_tokens", "input_characters", "tool_payload_characters", "latency_ms", "success", "error_code", "metadata"}
    data = {key: value for key, value in payload.items() if key in allowed}
    db.add(LLMUsage(**{("usage_metadata" if key == "metadata" else key): value for key, value in data.items()}))
    db.commit()
    return {"status": "recorded"}


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
def update_profile(payload: ProfileUpdate, db: Session = Depends(get_db)):
    profile = db.get(Profile, 1)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    allowed = {"name", "tagline", "location", "focus", "experience", "availability_status", "availability_detail", "about"}
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key in allowed:
            setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return {key: getattr(profile, key) for key in allowed}


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
    return search_portfolio_service(db, q, page, page_size)


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


app.include_router(public_projects.router)
app.include_router(admin_content.router)
app.include_router(admin_sync.router)
app.include_router(cv_router.router)
app.include_router(assets.router)


# Backward-compatible names previously defined on app.main; imported by tests/tooling.
_validate_cv_patch = cv_service.validate_cv_patch
_apply_cv_patch = cv_service.apply_cv_patch


# Host the Telegram webhook in the same Render service as the portfolio API.
# This keeps one always-on instance while preserving /telegram/webhook.
try:
    from bot.app.main import app as telegram_app
except ModuleNotFoundError:
    telegram_app = None
if telegram_app is not None:
    app.mount("/", telegram_app)
