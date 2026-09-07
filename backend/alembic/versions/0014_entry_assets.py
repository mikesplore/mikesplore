"""Attach existing site assets to entries."""
from alembic import op
import sqlalchemy as sa

revision = "0014_entry_assets"
down_revision = "0013_contact_integrity"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "entry_assets",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("entry_id", sa.UUID, sa.ForeignKey("entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("site_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("alt_text", sa.Text),
        sa.Column("caption", sa.Text),
        sa.Column("custom_order", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_unique_constraint("uq_entry_assets_entry_asset_role", "entry_assets", ["entry_id", "asset_id", "role"])

def downgrade():
    op.drop_table("entry_assets")
