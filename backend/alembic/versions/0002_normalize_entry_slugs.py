"""Normalize duplicate hyphens in entry slugs."""
from alembic import op

revision = "0002_normalize_entry_slugs"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("UPDATE entries SET slug = trim(both '-' from regexp_replace(slug, '-+', '-', 'g'))")

def downgrade():
    pass
