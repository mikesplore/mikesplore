"""Public project, technology, media, relationship, and content-block endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    ArchitectureDecision,
    Badge,
    CodeSnippet,
    Document,
    Entry,
    EntryAsset,
    EntryTechnology,
    Highlight,
    Metric,
    Quote,
    Relationship,
    Repository,
    SiteAsset,
    Technology,
    TopologyStep,
)

router = APIRouter(tags=["projects"])


def _project_blocks(project_id, db: Session) -> dict:
    def serialize(model, order_column):
        rows = db.scalars(select(model).where(model.entry_id == project_id).order_by(order_column)).all()
        return [{key: value for key, value in row.__dict__.items() if key != "_sa_instance_state" and value is not None} | {"id": str(row.id), "entry_id": str(row.entry_id)} for row in rows]

    return {
        "topology": serialize(TopologyStep, TopologyStep.order_index),
        "metrics": serialize(Metric, Metric.order_index),
        "decisions": serialize(ArchitectureDecision, ArchitectureDecision.order_index),
        "highlights": serialize(Highlight, Highlight.order_index),
        "quotes": serialize(Quote, Quote.id),
        "snippets": serialize(CodeSnippet, CodeSnippet.order_index),
        "documents": serialize(Document, Document.order_index),
        "badges": serialize(Badge, Badge.order_index),
    }


def _project_json(project: Entry, repositories: list[Repository], technologies: list[Technology], blocks: dict, assets: list[tuple[EntryAsset, SiteAsset]]) -> dict:
    return {"id": str(project.id), "slug": project.slug, "title": project.title, "blurb": project.blurb,
            "summary": project.blurb, "tags": project.tags or [], "technologies": [technology.name for technology in technologies],
            "links": {"repo": next((repo.url for repo in repositories if repo.is_primary), repositories[0].url if repositories else None)},
            "repositories": [{"name": repo.name, "url": repo.url, "is_primary": repo.is_primary, "role_label": repo.role_label, "primary_language": repo.primary_language, "link_label": repo.link_label} for repo in repositories if repo.is_visible],
            "content_blocks": blocks, "media": [{"id": asset.id, "role": link.role, "url": asset.url, "label": asset.label, "alt_text": link.alt_text, "caption": link.caption, "custom_order": link.custom_order} for link, asset in assets], "is_featured": project.is_featured, "icon_label": project.icon_label, "icon_url": project.icon_url, "status": project.status, "version": project.version, "license": project.license, "category": project.category, "author_role": project.author_role, "origin": project.origin, "started_at": project.started_at, "ended_at": project.ended_at, "template": project.template}


@router.get("/projects")
@router.get("/api/v1/projects")
def list_projects(
    response: Response,
    category: str | None = None,
    status: str | None = None,
    technology: str | None = None,
    featured: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = select(Entry).where(Entry.content_type == "project", Entry.is_visible.is_(True))
    if category:
        query = query.where(Entry.category == category)
    if status:
        query = query.where(Entry.status == status)
    if featured is not None:
        query = query.where(Entry.is_featured.is_(featured))
    if technology:
        query = query.join(EntryTechnology, EntryTechnology.entry_id == Entry.id).join(Technology, Technology.id == EntryTechnology.technology_id).where(Technology.name.ilike(technology))
    query = query.order_by(Entry.custom_order, Entry.title)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    response.headers["X-Total-Count"] = str(total)
@router.get("/projects/{slug}")
@router.get("/api/v1/projects/{slug}")
def get_project(slug: str, db: Session = Depends(get_db)):
    project = db.scalar(select(Entry).where(Entry.slug == slug, Entry.content_type == "project", Entry.is_visible.is_(True)))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    repos = db.scalars(select(Repository).where(Repository.entry_id == project.id, Repository.is_visible.is_(True)).order_by(Repository.custom_order)).all()
    technologies = db.scalars(select(Technology).join(EntryTechnology, EntryTechnology.technology_id == Technology.id).where(EntryTechnology.entry_id == project.id)).all()
    assets = db.execute(select(EntryAsset, SiteAsset).join(SiteAsset, EntryAsset.asset_id == SiteAsset.id).where(EntryAsset.entry_id == project.id).order_by(EntryAsset.custom_order)).all()
    return _project_json(project, repos, technologies, _project_blocks(project.id, db), assets)


@router.get("/technologies")
@router.get("/api/v1/technologies")
def list_technologies(db: Session = Depends(get_db)):
    return [{"id": str(item.id), "name": item.name, "category": item.category, "icon_url": item.icon_url} for item in db.scalars(select(Technology).order_by(Technology.name)).all()]


@router.get("/api/v1/projects/{slug}/media")
def project_media(slug: str, db: Session = Depends(get_db)):
    project = db.scalar(select(Entry).where(Entry.slug == slug, Entry.content_type == "project", Entry.is_visible.is_(True)))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return [{"id": link.id, "role": link.role, "url": asset.url, "label": asset.label, "alt_text": link.alt_text, "caption": link.caption, "custom_order": link.custom_order} for link, asset in db.execute(select(EntryAsset, SiteAsset).join(SiteAsset, EntryAsset.asset_id == SiteAsset.id).where(EntryAsset.entry_id == project.id).order_by(EntryAsset.custom_order)).all()]


@router.get("/api/v1/projects/{slug}/relationships")
def project_relationships(slug: str, db: Session = Depends(get_db)):
    project = db.scalar(select(Entry).where(Entry.slug == slug, Entry.content_type == "project", Entry.is_visible.is_(True)))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    result = []
    for relation in db.scalars(select(Relationship).where(Relationship.subject_type == "entry", Relationship.subject_id == project.id)).all():
        target = None
        if relation.object_type == "entry":
            target = db.scalar(select(Entry).where(Entry.id == relation.object_id, Entry.is_visible.is_(True)))
            display = {"id": str(target.id), "slug": target.slug, "title": target.title, "content_type": target.content_type} if target else None
        elif relation.object_type == "technology":
            target = db.get(Technology, relation.object_id)
            display = {"id": str(target.id), "name": target.name, "category": target.category, "icon_url": target.icon_url} if target else None
        elif relation.object_type == "repository":
            target = db.get(Repository, relation.object_id)
            parent = db.scalar(select(Entry).where(Entry.id == target.entry_id, Entry.is_visible.is_(True))) if target else None
            display = {"id": str(target.id), "name": target.name, "url": target.url} if target and parent else None
        else:
            display = None
        if display:
            result.append({"predicate": relation.predicate, "note": relation.note, "object_type": relation.object_type, "object": display})
    return result


@router.get("/entries/{entry_id}/content-blocks")
@router.get("/api/v1/entries/{entry_id}/content-blocks")
def entry_content_blocks(entry_id: UUID, db: Session = Depends(get_db)):
    entry = db.scalar(select(Entry).where(Entry.id == entry_id, Entry.is_visible.is_(True)))
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return _project_blocks(entry.id, db)
    projects = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return [_project_json(project, db.scalars(select(Repository).where(Repository.entry_id == project.id, Repository.is_visible.is_(True)).order_by(Repository.custom_order)).all(), db.scalars(select(Technology).join(EntryTechnology, EntryTechnology.technology_id == Technology.id).where(EntryTechnology.entry_id == project.id)).all(), _project_blocks(project.id, db), db.execute(select(EntryAsset, SiteAsset).join(SiteAsset, EntryAsset.asset_id == SiteAsset.id).where(EntryAsset.entry_id == project.id).order_by(EntryAsset.custom_order)).all()) for project in projects]