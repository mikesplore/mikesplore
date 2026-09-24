"""Portfolio-derived CV assembly, tailoring patch application, and PDF management."""

import hashlib
from html import unescape
import json
from io import BytesIO
from pathlib import Path
import re
import tempfile
from uuid import uuid4

try:
    import boto3
except ImportError:  # R2 support is optional for read-only and test usage.
    boto3 = None

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..cv_renderer import render as render_pdf
from ..models import (
    Certificate,
    CvVersion,
    Education,
    Entry,
    EntryTechnology,
    Highlight,
    Profile,
    ProfileLink,
    SkillGroup,
    Technology,
)
from .sync import slugify


def validate_cv_data(data: dict) -> dict:
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


def cv_base_hash(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def project_id(project: dict) -> str:
    return str(project.get("id") or project.get("slug") or slugify(project.get("name", "")))


def _plain_text(value: str | None) -> str:
    text = unescape(str(value or ""))
    return " ".join(re.sub(r"<[^>]*>", " ", text).split())


def _link_value(links: list[ProfileLink], *names: str) -> str | None:
    wanted = tuple(name.lower() for name in names)
    link = next((item for item in links if any(name in item.name.lower() for name in wanted)), None)
    if not link:
        return None
    value = (link.url or link.handle or "").strip()
    if value.startswith(("mailto:", "tel:")):
        value = value.split(":", 1)[1]
    return value or None


def build_cv_data(db: Session) -> dict:
    """Assemble the renderer's existing CV data shape from current portfolio rows."""
    profile = db.get(Profile, 1)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    links = db.scalars(
        select(ProfileLink).where(ProfileLink.is_visible.is_(True)).order_by(ProfileLink.custom_order)
    ).all()
    contact = {
        "location": profile.location,
        "email": _link_value(links, "email"),
        "phone": _link_value(links, "phone", "mobile"),
        "website": _link_value(links, "website", "portfolio", "site"),
        "github": _link_value(links, "github"),
    }
    skills = [
        {"category": group.category, "items": [str(item) for item in (group.skills or [])]}
        for group in db.scalars(
            select(SkillGroup).where(SkillGroup.is_visible.is_(True)).order_by(SkillGroup.custom_order)
        ).all()
    ]

    project_rows = db.scalars(
        select(Entry)
        .where(Entry.content_type == "project", Entry.is_visible.is_(True))
        .order_by(Entry.custom_order, Entry.date.desc().nullslast(), Entry.title)
        .limit(100)
    ).all()
    projects = []
    project_ids = [project.id for project in project_rows]
    stacks: dict = {}
    highlights_by_project: dict = {}
    if project_ids:
        for entry_id, technology_name in db.execute(
            select(EntryTechnology.entry_id, Technology.name)
            .join(Technology, EntryTechnology.technology_id == Technology.id)
            .where(EntryTechnology.entry_id.in_(project_ids))
            .order_by(Technology.name)
        ).all():
            stacks.setdefault(entry_id, []).append(technology_name)
        for highlight in db.scalars(
            select(Highlight)
            .where(Highlight.entry_id.in_(project_ids))
            .order_by(Highlight.entry_id, Highlight.order_index)
        ).all():
            highlights_by_project.setdefault(highlight.entry_id, []).append(highlight)

    for project in project_rows:
        stack = stacks.get(project.id, [])
        highlights = highlights_by_project.get(project.id, [])
        bullets = [
            _plain_text(item.description or item.title)
            for item in highlights
            if _plain_text(item.description or item.title)
        ][:6]
        if not bullets and _plain_text(project.blurb):
            bullets = [_plain_text(project.blurb)]
        date_value = project.date or project.started_at or project.ended_at
        date_label = str(date_value.year if hasattr(date_value, "year") else date_value or project.year or "")
        projects.append({
            "id": project.slug,
            "name": project.title,
            "date": date_label,
            "stack": ", ".join(stack),
            "bullets": bullets,
        })

    certificates = [
        item.title
        for item in db.scalars(
            select(Certificate).where(Certificate.is_visible.is_(True)).order_by(Certificate.custom_order)
        ).all()
    ]
    competitions = db.scalars(
        select(Entry)
        .where(Entry.content_type == "hackathon", Entry.is_visible.is_(True))
        .order_by(Entry.custom_order, Entry.date.desc().nullslast(), Entry.title)
    ).all()
    certificates.extend(
        f"{item.title} - {item.status}" if item.status else item.title
        for item in competitions
    )
    education = [
        {
            "institution": item.school,
            "degree": f"{item.degree} ({item.period})" if item.period else item.degree,
        }
        for item in db.scalars(select(Education).order_by(Education.custom_order)).all()
    ]

    about = _plain_text(profile.about)
    language_skills = next(
        (group["items"] for group in skills if "language" in group["category"].lower()),
        [],
    )
    additional_info = {}
    if language_skills:
        additional_info["languages"] = ", ".join(language_skills)
    summary_parts = [about]
    if profile.focus:
        summary_parts.append(profile.focus)
    if profile.experience:
        summary_parts.append(f"Experience: {profile.experience}")
    summary = " ".join(part for part in summary_parts if part) or profile.tagline or ""

    return {
        "name": profile.name,
        "title": profile.tagline or profile.focus or "",
        "contact": contact,
        "summary": summary,
        "skills": skills,
        "projects": projects,
        "certifications": certificates,
        "education": education,
        "additional_info": additional_info,
    }


def validate_cv_patch(patch: dict) -> dict:
    required = {"summary", "selected_projects", "selected_skills"}
    if not isinstance(patch, dict) or not required.issubset(patch):
        raise HTTPException(status_code=422, detail="CV patch must contain summary, selected_projects, and selected_skills")
    summary = patch["summary"]
    if not isinstance(summary, dict) or set(summary) != {"old", "new"} or not all(isinstance(summary[key], str) for key in summary):
        raise HTTPException(status_code=422, detail="CV summary patch must contain old and new text")
    if not isinstance(patch["selected_projects"], list) or not all(isinstance(item, str) for item in patch["selected_projects"]):
        raise HTTPException(status_code=422, detail="selected_projects must be a list of stable IDs")
    if not isinstance(patch["selected_skills"], dict) or any(not isinstance(value, list) or not all(isinstance(item, str) for item in value) for value in patch["selected_skills"].values()):
        raise HTTPException(status_code=422, detail="selected_skills must map categories to skill names")
    if not patch["selected_projects"] or not any(patch["selected_skills"].values()):
        raise HTTPException(status_code=422, detail="The job must match at least one verified project and skill")
    # Return only the render contract. Providers may include harmless metadata
    # around an otherwise valid patch.
    return {
        "summary": {"old": summary["old"], "new": summary["new"]},
        "selected_projects": list(patch["selected_projects"]),
        "selected_skills": dict(patch["selected_skills"]),
    }
def apply_cv_patch(base: dict, patch: dict) -> dict:
    validate_cv_data(base)
    patch = validate_cv_patch(patch)
    projects = {project_id(project): project for project in base["projects"]}
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


def render_cv(db: Session, payload: dict) -> dict:
    """Render a tailored CV from current portfolio records and store its snapshot."""
    base = build_cv_data(db)
    if payload.get("base_revision") != cv_base_hash(base):
        raise HTTPException(status_code=409, detail="Portfolio data changed while this proposal was pending; run /apply again")
    patch = validate_cv_patch(payload.get("patch") or {})
    data = apply_cv_patch(base, patch)
    job_description = str(payload.get("job_description") or "").strip()
    label = str(payload.get("label") or "Tailored CV")[:255]
    if not job_description:
        raise HTTPException(status_code=422, detail="job_description is required")
    if not all((settings.r2_endpoint_url, settings.r2_access_key_id, settings.r2_secret_access_key, settings.r2_bucket_name, settings.r2_public_base_url)):
        raise HTTPException(status_code=503, detail="R2 storage is not configured")
    version_id = uuid4()
    with tempfile.TemporaryDirectory() as directory:
        output_path = Path(directory) / "cv.pdf"
        render_pdf(data, str(output_path))
        pdf_bytes = output_path.read_bytes()
    object_key = f"cv-versions/{version_id}.pdf"
    client = boto3.client("s3", endpoint_url=settings.r2_endpoint_url, aws_access_key_id=settings.r2_access_key_id, aws_secret_access_key=settings.r2_secret_access_key, region_name="auto")
    client.upload_fileobj(BytesIO(pdf_bytes), settings.r2_bucket_name, object_key, ExtraArgs={"ContentType": "application/pdf"})
    pdf_url = f"{settings.r2_public_base_url.rstrip('/')}/{object_key}"
    db.add(CvVersion(id=version_id, label=label, job_description=job_description, data=data, patch=patch, base_snapshot=base, pdf_url=pdf_url))
    db.commit()
    return {"id": str(version_id), "label": label, "pdf_url": pdf_url}


def render_current_cv(db: Session) -> dict:
    """Render and store a fresh, untailored CV from current visible portfolio data."""
    data = validate_cv_data(build_cv_data(db))
    if not all((settings.r2_endpoint_url, settings.r2_access_key_id, settings.r2_secret_access_key, settings.r2_bucket_name, settings.r2_public_base_url)):
        raise HTTPException(status_code=503, detail="R2 storage is not configured")
    version_id = uuid4()
    label = "Current Portfolio CV"
    job_description = "Current portfolio CV generated from live portfolio data."
    with tempfile.TemporaryDirectory() as directory:
        output_path = Path(directory) / "cv.pdf"
        render_pdf(data, str(output_path))
        pdf_bytes = output_path.read_bytes()
    object_key = f"cv-versions/{version_id}.pdf"
    client = boto3.client("s3", endpoint_url=settings.r2_endpoint_url, aws_access_key_id=settings.r2_access_key_id, aws_secret_access_key=settings.r2_secret_access_key, region_name="auto")
    client.upload_fileobj(BytesIO(pdf_bytes), settings.r2_bucket_name, object_key, ExtraArgs={"ContentType": "application/pdf"})
    pdf_url = f"{settings.r2_public_base_url.rstrip('/')}/{object_key}"
    db.add(CvVersion(id=version_id, label=label, job_description=job_description, data=data, patch={}, base_snapshot=data, pdf_url=pdf_url))
    db.commit()
    return {"id": str(version_id), "label": label, "pdf_url": pdf_url}
    return patch
