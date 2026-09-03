"""Add skills and site settings collections."""
from alembic import op
import sqlalchemy as sa

revision = "0003_add_skills_and_settings"
down_revision = "0002_normalize_entry_slugs"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("skill_groups", sa.Column("id", sa.Integer, primary_key=True, autoincrement=True), sa.Column("category", sa.String(128), nullable=False), sa.Column("skills", sa.JSON, nullable=False), sa.Column("custom_order", sa.Integer, nullable=False, server_default="0"), sa.Column("is_visible", sa.Boolean, nullable=False, server_default=sa.true()))
    op.create_table("site_settings", sa.Column("key", sa.String(128), primary_key=True), sa.Column("value", sa.JSON, nullable=False))

def downgrade():
    op.drop_table("site_settings")
    op.drop_table("skill_groups")
