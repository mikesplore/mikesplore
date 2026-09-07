import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Entry(Base):
    __tablename__ = "entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    content_type: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(255))
    blurb: Mapped[str] = mapped_column(Text)
    date: Mapped[date | None] = mapped_column(Date)
    year: Mapped[int | None] = mapped_column(Integer)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    custom_order: Mapped[int] = mapped_column(Integer, default=0)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    source: Mapped[dict] = mapped_column(JSONB, default=dict)
    icon_label: Mapped[str | None] = mapped_column(Text)
    icon_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str | None] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    author_role: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[date | None] = mapped_column(Date)
    ended_at: Mapped[date | None] = mapped_column(Date)
    template: Mapped[str] = mapped_column(Text, default="standard")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Repository(Base):
    __tablename__ = "repositories"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text, unique=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    custom_order: Mapped[int] = mapped_column(Integer, default=0)
    repo_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    role_label: Mapped[str | None] = mapped_column(Text)
    primary_language: Mapped[str | None] = mapped_column(Text)
    link_label: Mapped[str | None] = mapped_column(Text)
    synced_from_github: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Technology(Base):
    __tablename__ = "technologies"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, unique=True)
    category: Mapped[str | None] = mapped_column(Text)
    icon_url: Mapped[str | None] = mapped_column(Text)


class EntryTechnology(Base):
    __tablename__ = "entry_technologies"
    entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    technology_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)


class RepositoryTechnology(Base):
    __tablename__ = "repository_technologies"
    repository_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    technology_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)


class EntryAsset(Base):
    __tablename__ = "entry_assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    asset_id: Mapped[int] = mapped_column(Integer, index=True)
    role: Mapped[str] = mapped_column(String(64))
    alt_text: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)
    custom_order: Mapped[int] = mapped_column(Integer, default=0)


class ContentBlockBase:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)


class TopologyStep(ContentBlockBase, Base):
    __tablename__ = "topology_steps"
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    role_label: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    footnote_label: Mapped[str | None] = mapped_column(Text)
    footnote_value: Mapped[str | None] = mapped_column(Text)


class Metric(ContentBlockBase, Base):
    __tablename__ = "metrics"
    label: Mapped[str | None] = mapped_column(Text)
    value: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(Text)
    group_tag: Mapped[str | None] = mapped_column(Text)
    is_highlighted: Mapped[bool] = mapped_column(Boolean, default=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class ArchitectureDecision(ContentBlockBase, Base):
    __tablename__ = "architecture_decisions"
    icon: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class Highlight(ContentBlockBase, Base):
    __tablename__ = "highlights"
    icon: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class Quote(ContentBlockBase, Base):
    __tablename__ = "quotes"
    quote_text: Mapped[str | None] = mapped_column(Text)
    attribution_name: Mapped[str | None] = mapped_column(Text)
    attribution_role: Mapped[str | None] = mapped_column(Text)
    context_label: Mapped[str | None] = mapped_column(Text, default="Why I Built This")


class CodeSnippet(ContentBlockBase, Base):
    __tablename__ = "code_snippets"
    label: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(Text)
    code: Mapped[str | None] = mapped_column(Text)
    is_copyable: Mapped[bool] = mapped_column(Boolean, default=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class Document(ContentBlockBase, Base):
    __tablename__ = "documents"
    title: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(Text)
    link_style: Mapped[str | None] = mapped_column(Text, default="secondary")
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class Badge(ContentBlockBase, Base):
    __tablename__ = "badges"
    label: Mapped[str | None] = mapped_column(Text)
    style: Mapped[str | None] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_type: Mapped[str] = mapped_column(Text)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    predicate: Mapped[str] = mapped_column(Text)
    object_type: Mapped[str] = mapped_column(Text)
    object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    note: Mapped[str | None] = mapped_column(Text)


class Profile(Base):
    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    tagline: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    focus: Mapped[str | None] = mapped_column(String(255))
    experience: Mapped[str | None] = mapped_column(String(255))
    availability_status: Mapped[str | None] = mapped_column(String(255))
    availability_detail: Mapped[str | None] = mapped_column(Text)
    about: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255))
    image_url: Mapped[str] = mapped_column(Text)
    custom_order: Mapped[int] = mapped_column(Integer, default=0)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)


class SkillGroup(Base):
    __tablename__ = "skill_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(128))
    skills: Mapped[list] = mapped_column(JSONB)
    custom_order: Mapped[int] = mapped_column(Integer, default=0)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)


class SiteSetting(Base):
    __tablename__ = "site_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB)


class CvVersion(Base):
    __tablename__ = "cv_versions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label: Mapped[str] = mapped_column(String(255))
    job_description: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSONB)
    patch: Mapped[dict] = mapped_column(JSONB, default=dict)
    base_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    pdf_url: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProfileLink(Base):
    __tablename__ = "profile_links"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64))
    url: Mapped[str] = mapped_column(Text)
    label: Mapped[str | None] = mapped_column(String(255))
    handle: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(32))
    custom_order: Mapped[int] = mapped_column(Integer, default=0)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    normalized_name: Mapped[str] = mapped_column(String(64), default="")
    normalized_url: Mapped[str] = mapped_column(Text, default="")


class Education(Base):
    __tablename__ = "education"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    degree: Mapped[str] = mapped_column(String(255))
    school: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    period: Mapped[str | None] = mapped_column(String(128))
    custom_order: Mapped[int] = mapped_column(Integer, default=0)


class BucketListItem(Base):
    __tablename__ = "bucket_list_items"
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    remark: Mapped[str | None] = mapped_column(Text)
    custom_order: Mapped[int] = mapped_column(Integer, default=0)


class SiteAsset(Base):
    __tablename__ = "site_assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_type: Mapped[str] = mapped_column(String(32))
    url: Mapped[str] = mapped_column(Text)
    label: Mapped[str | None] = mapped_column(String(255))


class AdminOperation(Base):
    __tablename__ = "admin_operations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    instruction: Mapped[str] = mapped_column(Text)
    operation: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    error_detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    telegram_user_id: Mapped[int] = mapped_column(BigInteger)
    resource: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(16))
    record_id: Mapped[str | None] = mapped_column(String(160))
    before_value: Mapped[dict | None] = mapped_column(JSONB)
    after_value: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
