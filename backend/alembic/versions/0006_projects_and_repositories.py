"""Create curated projects and repository relationships."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_projects_and_repositories"
down_revision = "0005_cv_patch_columns"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(160), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("blurb", sa.Text, nullable=False),
        sa.Column("tech_stack", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("tags", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("details", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("links", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("media", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_visible", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_featured", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("custom_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "project_repositories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.Text, nullable=False, unique=True),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("custom_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
    )
    op.execute("""
        INSERT INTO projects (id, slug, title, blurb, tech_stack, tags, details, links, media,
                              is_visible, is_featured, custom_order)
        SELECT id, slug, title, blurb, tech_stack, tags, details, links, media,
               is_visible, is_featured, custom_order
        FROM entries WHERE content_type = 'project'
    """)
    op.execute("""
        INSERT INTO project_repositories (id, project_id, name, url, is_primary, metadata)
        SELECT gen_random_uuid(), id, title, source->>'key', true, source
        FROM entries
        WHERE content_type = 'project' AND source->>'provider' = 'github'
          AND source->>'key' IS NOT NULL
    """)

def downgrade():
    op.drop_table("project_repositories")
    op.drop_table("projects")
