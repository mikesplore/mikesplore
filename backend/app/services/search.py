"""Public, admin, and CV search helpers backed by verified database content."""

import re

from sqlalchemy import cast, func, or_, select, String
from sqlalchemy.orm import Session

from ..models import (
    BucketListItem,
    Certificate,
    Education,
    Entry,
    EntryAsset,
    Profile,
    ProfileLink,
    Repository,
    RolePolicy,
    SiteAsset,
    SiteSetting,
    SkillGroup,
    Technology,
)


def model_record(item) -> dict:
    """Serialize every mapped column of a database row to a plain dict."""
    return {attribute.key: getattr(item, attribute.key) for attribute in item.__mapper__.column_attrs}


def search_portfolio(db: Session, q: str, page: int, page_size: int) -> dict:
    term = f"%{q}%"
    terms = [word.lower() for word in re.findall(r"[a-z0-9]+", q.lower()) if len(word) > 2]
    search_vector = func.to_tsvector("simple", func.concat_ws(" ", Entry.title, Entry.blurb, cast(Entry.tags, String), cast(Entry.source, String)))
    search_query = func.plainto_tsquery("simple", q)
    query = select(Entry).where(Entry.is_visible.is_(True), or_(Entry.title.ilike(term), Entry.blurb.ilike(term), cast(Entry.tags, String).ilike(term), search_vector.op("@@")(search_query))).order_by(Entry.custom_order, Entry.date.desc().nullslast())
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


def admin_search(db: Session, q: str) -> list[dict]:
    models = {"entries": Entry, "certificates": Certificate, "assets": SiteAsset, "links": ProfileLink, "skills": SkillGroup, "education": Education, "bucket-list": BucketListItem, "settings": SiteSetting, "role-policies": RolePolicy, "repositories": Repository, "technologies": Technology, "entry-assets": EntryAsset}
    terms = [term.lower() for term in re.findall(r"[a-z0-9]+", q.lower()) if len(term) > 2]
    results = []
    for resource, model in models.items():
        for item in db.scalars(select(model)).all():
            values = model_record(item)
            haystack = " ".join(str(value).lower() for value in values.values())
            score = sum(term in haystack for term in terms)
            if score:
                results.append({"resource": resource, "score": score, "record": values})
    return sorted(results, key=lambda result: result["score"], reverse=True)[:10]


def search_cv(db: Session, q: str) -> dict:
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