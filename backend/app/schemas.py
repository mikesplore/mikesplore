from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ContentType = Literal["project", "article", "hackathon", "event"]


class EntryBase(BaseModel):
    slug: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    content_type: ContentType
    title: str = Field(min_length=1, max_length=255)
    blurb: str
    date: date | None = None
    year: int | None = Field(default=None, ge=1900, le=2200)
    is_visible: bool = True
    is_featured: bool = False
    custom_order: int = 0
    tech_stack: list[str] = []
    tags: list[str] = []
    details: dict[str, Any] = {}
    links: dict[str, Any] = {}
    media: dict[str, Any] = {}
    source: dict[str, Any] = {}


class EntryCreate(EntryBase):
    pass


class EntryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str | None = Field(default=None, min_length=1, max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    content_type: ContentType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    blurb: str | None = None
    date: date | None = None
    year: int | None = Field(default=None, ge=1900, le=2200)
    is_visible: bool | None = None
    is_featured: bool | None = None
    custom_order: int | None = None
    tech_stack: list[str] | None = None
    tags: list[str] | None = None
    details: dict[str, Any] | None = None
    links: dict[str, Any] | None = None
    media: dict[str, Any] | None = None
    source: dict[str, Any] | None = None


class EntryRead(EntryBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime
