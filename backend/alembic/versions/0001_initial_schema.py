"""Create portfolio content schema."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSON = postgresql.JSONB()
empty_array = sa.text("ARRAY[]::varchar[]")
empty_json = sa.text("'{}'::jsonb")
uuid_default = sa.text("gen_random_uuid()")

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "entries",
        sa.Column("id", UUID, primary_key=True, server_default=uuid_default),
        sa.Column("slug", sa.String(160), nullable=False, unique=True),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("blurb", sa.Text, nullable=False),
        sa.Column("date", sa.Date, nullable=True), sa.Column("year", sa.Integer, nullable=True),
        sa.Column("is_visible", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_featured", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("custom_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tech_stack", postgresql.ARRAY(sa.String), nullable=False, server_default=empty_array),
        sa.Column("tags", postgresql.ARRAY(sa.String), nullable=False, server_default=empty_array),
        sa.Column("details", JSON, nullable=False, server_default=empty_json),
        sa.Column("links", JSON, nullable=False, server_default=empty_json),
        sa.Column("media", JSON, nullable=False, server_default=empty_json),
        sa.Column("source", JSON, nullable=False, server_default=empty_json),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("content_type IN ('project', 'article', 'hackathon', 'event')", name="ck_entries_content_type"),
    )
    op.create_index("ix_entries_public_order", "entries", ["is_visible", "custom_order", "date"])
    op.create_table("profile", sa.Column("id", sa.SmallInteger, primary_key=True), sa.Column("name", sa.String(255), nullable=False), sa.Column("tagline", sa.Text), sa.Column("location", sa.String(255)), sa.Column("focus", sa.String(255)), sa.Column("experience", sa.String(255)), sa.Column("availability_status", sa.String(255)), sa.Column("availability_detail", sa.Text), sa.Column("about", sa.Text), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table("profile_links", sa.Column("id", UUID, primary_key=True, server_default=uuid_default), sa.Column("name", sa.String(64), nullable=False), sa.Column("url", sa.Text, nullable=False), sa.Column("label", sa.String(255)), sa.Column("handle", sa.String(255)), sa.Column("category", sa.String(32), nullable=False), sa.Column("custom_order", sa.Integer, nullable=False, server_default="0"), sa.Column("is_visible", sa.Boolean, nullable=False, server_default=sa.true()))
    op.create_table("education", sa.Column("id", UUID, primary_key=True, server_default=uuid_default), sa.Column("degree", sa.String(255), nullable=False), sa.Column("school", sa.String(255), nullable=False), sa.Column("location", sa.String(255)), sa.Column("period", sa.String(128)), sa.Column("custom_order", sa.Integer, nullable=False, server_default="0"))
    op.create_table("certificates", sa.Column("id", UUID, primary_key=True, server_default=uuid_default), sa.Column("title", sa.String(255), nullable=False), sa.Column("image_url", sa.Text, nullable=False), sa.Column("custom_order", sa.Integer, nullable=False, server_default="0"), sa.Column("is_visible", sa.Boolean, nullable=False, server_default=sa.true()))
    op.create_table("bucket_list_items", sa.Column("id", sa.String(160), primary_key=True), sa.Column("title", sa.String(255), nullable=False), sa.Column("done", sa.Boolean, nullable=False, server_default=sa.false()), sa.Column("remark", sa.Text), sa.Column("custom_order", sa.Integer, nullable=False, server_default="0"))
    op.create_table("site_assets", sa.Column("id", sa.SmallInteger, primary_key=True), sa.Column("asset_type", sa.String(32), nullable=False), sa.Column("url", sa.Text, nullable=False), sa.Column("label", sa.String(255)))

def downgrade():
    for table in ("site_assets", "bucket_list_items", "certificates", "education", "profile_links", "profile", "entries"):
        op.drop_table(table)
