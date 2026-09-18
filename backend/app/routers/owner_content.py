"""Owner-session resource listing and mutation gateway."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BucketListItem, Certificate, Education, Entry, ProfileLink, SkillGroup
from ..owner_auth import require_owner_session
from ..services.search import model_record

router = APIRouter(prefix="/owner/resources", tags=["owner"])
MODELS = {"projects": Entry, "certificates": Certificate, "links": ProfileLink, "skills": SkillGroup, "education": Education, "bucket-list": BucketListItem}


def model_for(resource: str):
    model = MODELS.get(resource)
    if not model:
        raise HTTPException(status_code=404, detail="Unsupported owner resource")
    return model


@router.get("/{resource}", dependencies=[Depends(require_owner_session)])
def list_owner_resource(resource: str, db: Session = Depends(get_db)):
    model = model_for(resource)
    query = select(model)
    if resource == "projects":
        query = query.where(Entry.content_type == "project")
    return [model_record(item) for item in db.scalars(query).all()]


@router.post("/{resource}", dependencies=[Depends(require_owner_session)])
def mutate_owner_resource(resource: str, payload: dict, db: Session = Depends(get_db)):
    model = model_for(resource)
    action = payload.pop("action", "update")
    identity = payload.pop("id", None)
    item = db.get(model, identity) if identity else None
    if action == "delete":
        if not item:
            raise HTTPException(status_code=404, detail="Owner resource not found")
        db.delete(item)
    elif action == "update":
        if not item:
            raise HTTPException(status_code=404, detail="Owner resource not found")
        for key, value in payload.items():
            if hasattr(item, key):
                setattr(item, key, value)
    elif action == "create":
        if resource == "projects":
            payload.setdefault("content_type", "project")
        if resource == "bucket-list":
            payload.setdefault("id", str(uuid.uuid4()))
        db.add(model(**{key: value for key, value in payload.items() if hasattr(model, key)}))
    else:
        raise HTTPException(status_code=400, detail="Unsupported owner mutation")
    db.commit()
    return {"status": action, "resource": resource, "id": str(getattr(item, "id", "")) if item else None}
