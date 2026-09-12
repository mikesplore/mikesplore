"""Base CV validation, tailoring patch application, and rendered PDF management."""

import hashlib
import json
from io import BytesIO
from pathlib import Path
import tempfile
from uuid import uuid4

try:
    import boto3
except ImportError:  # R2 support is optional for read-only and test usage.
    boto3 = None

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..cv_renderer import render as render_pdf
from ..models import CvVersion, SiteSetting
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
    return slugify(project.get("name", ""))


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
    """Render a tailored CV PDF from a validated patch and store it as a CvVersion."""
    setting = db.get(SiteSetting, "cv_data")
    if not setting:
        raise HTTPException(status_code=404, detail="Base CV JSON has not been configured")
    base = setting.value
    if payload.get("base_revision") != cv_base_hash(base):
        raise HTTPException(status_code=409, detail="The base CV changed while this patch was pending; run /apply again")
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
    return patch
