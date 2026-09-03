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
