"""Merge curated projects into entries and rename repositories."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_merge_projects_repositories"
down_revision = "0007_normalize_technologies"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""UPDATE entries e SET title=p.title, blurb=p.blurb, tech_stack=p.tech_stack, tags=p.tags,
        details=p.details, links=p.links, media=p.media, is_visible=p.is_visible,
        is_featured=p.is_featured, custom_order=p.custom_order, updated_at=p.updated_at
        FROM projects p WHERE e.slug=p.slug AND e.content_type='project'""")
    op.execute("""INSERT INTO entries (id,slug,content_type,title,blurb,tech_stack,tags,details,links,media,is_visible,is_featured,custom_order,created_at,updated_at)
        SELECT p.id,p.slug,'project',p.title,p.blurb,p.tech_stack,p.tags,p.details,p.links,p.media,p.is_visible,p.is_featured,p.custom_order,p.created_at,p.updated_at
        FROM projects p WHERE NOT EXISTS (SELECT 1 FROM entries e WHERE e.slug=p.slug)""")
    op.execute("ALTER TABLE project_repositories DROP CONSTRAINT project_repositories_project_id_fkey")
    op.execute("""UPDATE project_repositories r SET project_id=e.id FROM projects p JOIN entries e ON e.slug=p.slug WHERE r.project_id=p.id""")
    op.rename_table("project_repositories", "repositories")
    op.alter_column("repositories", "project_id", new_column_name="entry_id")
    op.create_foreign_key("repositories_entry_id_fkey", "repositories", "entries", ["entry_id"], ["id"], ondelete="CASCADE")
    for name in ("role_label", "primary_language", "link_label"):
        op.add_column("repositories", sa.Column(name, sa.Text))
    op.add_column("repositories", sa.Column("synced_from_github", sa.Boolean, nullable=False, server_default=sa.true()))
    op.add_column("repositories", sa.Column("last_synced_at", sa.DateTime(timezone=True)))
    op.create_table("repository_technologies",
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("technology_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("technologies.id", ondelete="CASCADE"), nullable=False),
        sa.PrimaryKeyConstraint("repository_id", "technology_id"))

def downgrade():
    op.drop_table("repository_technologies")
    op.drop_constraint("repositories_entry_id_fkey", "repositories", type_="foreignkey")
    for name in ("last_synced_at", "synced_from_github", "link_label", "primary_language", "role_label"):
        op.drop_column("repositories", name)
    op.alter_column("repositories", "entry_id", new_column_name="project_id")
    op.rename_table("repositories", "project_repositories")
    op.create_foreign_key("project_repositories_project_id_fkey", "project_repositories", "projects", ["project_id"], ["id"], ondelete="CASCADE")
