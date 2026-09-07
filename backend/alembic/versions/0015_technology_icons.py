"""Add technology icon references."""
from alembic import op
import sqlalchemy as sa

revision = "0015_technology_icons"
down_revision = "0014_entry_assets"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("technologies", sa.Column("icon_url", sa.Text))

def downgrade():
    op.drop_column("technologies", "icon_url")
