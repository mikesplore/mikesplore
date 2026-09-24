"""Protected CV base/tailoring endpoints and public CV-text search."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import require_service_key
from ..db import get_db
from ..services import cv as cv_service
from ..services.search import search_cv as search_cv_text

router = APIRouter(tags=["cv"])


@router.get("/admin/cv/base", dependencies=[Depends(require_service_key)])
def get_cv_base(db: Session = Depends(get_db)):
    return cv_service.get_cv_base(db)


@router.get("/admin/cv/portfolio-context", dependencies=[Depends(require_service_key)])
def get_cv_portfolio_context(db: Session = Depends(get_db)):
    data = cv_service.build_cv_data(db)
    return {"data": data, "revision": cv_service.cv_base_hash(data)}


@router.post("/admin/cv/base/validate", dependencies=[Depends(require_service_key)])
def validate_cv_base(payload: dict):
    return cv_service.validate_cv_data(payload)


@router.post("/admin/cv/base", dependencies=[Depends(require_service_key)])
def save_cv_base(payload: dict, db: Session = Depends(get_db)):
    if "data" in payload:
        return cv_service.save_cv_base(db, payload["data"], payload.get("base_revision"), payload.get("portfolio_revision"))
    # Backward-compatible body shape for the original cv-json upload flow.
    return cv_service.save_cv_base(db, payload)


@router.get("/admin/cv/profile", dependencies=[Depends(require_service_key)])
def get_cv_profile(db: Session = Depends(get_db)):
    data = cv_service.get_cv_base(db)["data"]
    return {"name": data.get("name"), "title": data.get("title"), "contact": data.get("contact"), "summary": data.get("summary"), "revision": cv_service.cv_base_hash(data)}


@router.get("/admin/cv/tailoring-context", dependencies=[Depends(require_service_key)])
def get_cv_tailoring_context(db: Session = Depends(get_db)):
    """Return only approved CV content for job tailoring."""
    data = cv_service.get_cv_base(db)["data"]
    projects = []
    for project in data.get("projects", [])[:20]:
        bullets = [str(bullet)[:500] for bullet in (project.get("bullets") or [])[:6]]
        stack = project.get("stack") or []
        if isinstance(stack, str):
            stack = [item.strip() for item in stack.split(",") if item.strip()]
        projects.append({"id": cv_service.project_id(project), "name": project["name"], "date": project.get("date"), "featured": project.get("featured", False), "stack": stack[:20], "bullets": bullets})
    skills = [{"category": group.get("category"), "items": (group.get("items") or [])[:30]} for group in data.get("skills", [])[:20]]
    return {"profile": {"name": data.get("name"), "title": data.get("title"), "summary": data.get("summary")}, "projects": projects, "skills": skills, "revision": cv_service.cv_base_hash(data)}


@router.get("/admin/cv/projects", dependencies=[Depends(require_service_key)])
def search_cv_projects(q: str = Query(default=""), db: Session = Depends(get_db)):
    data = cv_service.get_cv_base(db)["data"]
    term = q.lower().strip()
    results = []
    for project in data.get("projects", []):
        if not term or term in json.dumps(project).lower():
            results.append({"id": cv_service.project_id(project), "name": project["name"], "date": project.get("date"), "stack": project.get("stack"), "bullets": project.get("bullets", [])})
    return results[:5]


@router.get("/admin/cv/skills", dependencies=[Depends(require_service_key)])
def search_cv_skills(q: str = Query(default=""), db: Session = Depends(get_db)):
    data = cv_service.get_cv_base(db)["data"]
    term = q.lower().strip()
    return [{"category": group["category"], "items": [item for item in group["items"] if not term or term in item.lower() or term in group["category"].lower()]}
            for group in data.get("skills", []) if any(not term or term in item.lower() or term in group["category"].lower() for item in group["items"])]


@router.post("/admin/cv/render", dependencies=[Depends(require_service_key)])
def render_cv_version(payload: dict, db: Session = Depends(get_db)):
    try:
        return cv_service.render_cv(db, payload)
    except HTTPException as error:
        if error.status_code == 422:
            patch = payload.get("patch")
            summary = {"patch_keys": sorted(patch) if isinstance(patch, dict) else type(patch).__name__}
            if isinstance(patch, dict) and isinstance(patch.get("summary"), dict):
                summary["summary_keys"] = sorted(patch["summary"])
                summary["selected_projects_type"] = type(patch.get("selected_projects")).__name__
                summary["selected_skills_type"] = type(patch.get("selected_skills")).__name__
            error.detail = f"{error.detail} | observed={summary!r}"
        raise


@router.post("/admin/cv/render-base", dependencies=[Depends(require_service_key)])
def render_base_cv(db: Session = Depends(get_db)):
    return cv_service.render_base_cv(db)


@router.get("/cv/search")
def search_cv(q: str = Query(min_length=1), db: Session = Depends(get_db)):
    return search_cv_text(db, q)
