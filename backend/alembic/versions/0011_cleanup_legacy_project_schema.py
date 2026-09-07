"""Remove legacy project storage after unified-entry cutover."""
from alembic import op

revision = "0011_cleanup_legacy_project_schema"
down_revision = "0010_relationships"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("projects")
    for column in ("media", "links", "details", "tech_stack"):
        op.drop_column("entries", column)


def downgrade():
    raise RuntimeError("0011 is irreversible: restore the projects table and legacy JSONB data from backup/source commit")
