import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, func
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
    tech_stack: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    links: Mapped[dict] = mapped_column(JSONB, default=dict)
    media: Mapped[dict] = mapped_column(JSONB, default=dict)
    source: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


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
