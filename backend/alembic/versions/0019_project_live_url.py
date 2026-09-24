"""Add optional live/demo URL to entries."""

from alembic import op
import sqlalchemy as sa


revision = "0019_project_live_url"
down_revision = "0018_llm_usage"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("entries", sa.Column("live_url", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("entries", "live_url")
