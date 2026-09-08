"""Normalize and protect profile-link identities."""
from alembic import op
import sqlalchemy as sa

revision = "0013_contact_integrity"
down_revision = "0012_admin_operations"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("profile_links", sa.Column("normalized_name", sa.String(64), nullable=False, server_default=""))
    op.add_column("profile_links", sa.Column("normalized_url", sa.Text, nullable=False, server_default=""))
    op.execute("UPDATE profile_links SET normalized_name=lower(trim(name)), normalized_url=regexp_replace(lower(trim(url)), '/+$', '')")
    # Older imports could contain repeated links. Keep one deterministic row
    # for each normalized identity before enforcing the new uniqueness invariant.
    op.execute("""
        DELETE FROM profile_links duplicate
        USING profile_links keeper
        WHERE duplicate.normalized_name = keeper.normalized_name
          AND duplicate.normalized_url = keeper.normalized_url
          AND duplicate.id > keeper.id
    """)
    op.create_index("ux_profile_links_identity", "profile_links", ["normalized_name", "normalized_url"], unique=True)

def downgrade():
    op.drop_index("ux_profile_links_identity", table_name="profile_links")
    op.drop_column("profile_links", "normalized_url")
    op.drop_column("profile_links", "normalized_name")
