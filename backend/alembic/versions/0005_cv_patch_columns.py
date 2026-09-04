"""Store CV patches and base snapshots with rendered versions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_cv_patch_columns"
down_revision = "0004_add_cv_versions"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("cv_versions", sa.Column("patch", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("cv_versions", sa.Column("base_snapshot", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")))

def downgrade():
    op.drop_column("cv_versions", "base_snapshot")
    op.drop_column("cv_versions", "patch")
