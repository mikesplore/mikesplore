"""Add portfolio work experience records."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0020_work_experience"
down_revision = "0019_project_live_url"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "work_experience",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("organization", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255)),
        sa.Column("period", sa.String(length=128)),
        sa.Column("employment_type", sa.String(length=128)),
        sa.Column("description", sa.Text()),
        sa.Column("highlights", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("custom_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade():
    op.drop_table("work_experience")
