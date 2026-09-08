"""Add data-driven CV role policies."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0016_role_policies"
down_revision = "0015_technology_icons"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "role_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role_family", sa.String(128), nullable=False, unique=True),
        sa.Column("titles", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("related_skills", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("related_projects", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("evidence_requirements", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("excluded_claims", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("confidence", sa.String(32)),
        sa.Column("source", sa.String(64)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("role_policies")
