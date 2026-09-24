from __future__ import annotations

from datetime import date as DateValue
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ContentType = Literal["project", "article", "hackathon", "event"]
LinkCategory = Literal["professional", "social", "contact"]


class EntryBase(BaseModel):
    slug: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    content_type: ContentType
    title: str = Field(min_length=1, max_length=255)
    blurb: str
    live_url: str | None = None
    date: DateValue | None = None
    year: int | None = Field(default=None, ge=1900, le=2200)
    is_visible: bool = True
    is_featured: bool = False
    custom_order: int = 0
    tags: list[str] = []
    source: dict[str, Any] = {}

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        import re
        return re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")

    @field_validator("live_url", mode="before")
    @classmethod
    def normalize_live_url(cls, value: str | None) -> str | None:
        if not value:
            return value
        value = str(value).strip()
        if not value.lower().startswith("https://"):
            if "://" not in value:
                value = "https://" + value
            else:
                raise ValueError("live_url must use HTTPS")
        return value


class EntryCreate(EntryBase):
    pass


class EntryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str | None = Field(default=None, min_length=1, max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    content_type: ContentType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    blurb: str | None = None
    live_url: str | None = None
    date: DateValue | None = None
    year: int | None = Field(default=None, ge=1900, le=2200)
    is_visible: bool | None = None
    is_featured: bool | None = None
    custom_order: int | None = None
    tags: list[str] | None = None
    source: dict[str, Any] | None = None

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value: str | None) -> str | None:
        import re
        if value is None:
            return None
        return re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()).strip("-")

    @field_validator("live_url", mode="before")
    @classmethod
    def normalize_live_url(cls, value: str | None) -> str | None:
        if not value:
            return value
        value = str(value).strip()
        if not value.lower().startswith("https://"):
            if "://" not in value:
                value = "https://" + value
            else:
                raise ValueError("live_url must use HTTPS")
        return value


class EntryRead(EntryBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    tagline: str | None = None
    location: str | None = None
    focus: str | None = None
    experience: str | None = None
    availability_status: str | None = None
    availability_detail: str | None = None
    about: str | None = None


class ProfileLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=64)
    url: str = Field(min_length=1, max_length=2048)
    label: str | None = Field(default=None, max_length=255)
    handle: str | None = Field(default=None, max_length=255)
    category: LinkCategory
    custom_order: int = 0
    is_visible: bool = True


class ProfileLinkUpdate(ProfileLinkCreate):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    category: LinkCategory | None = None


class AdminLinkMutation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["create", "update", "delete"]
    id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class BulkLinkMutation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operations: list[AdminLinkMutation] = Field(min_length=1, max_length=50)
