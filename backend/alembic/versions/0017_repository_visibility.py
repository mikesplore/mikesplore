"""Add per-repository visibility."""
from alembic import op
import sqlalchemy as sa

revision = "0017_repository_visibility"
down_revision = "0016_role_policies"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("repositories", sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    op.drop_column("repositories", "is_visible")
