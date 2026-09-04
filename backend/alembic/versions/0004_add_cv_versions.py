"""Store rendered tailored CV versions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_add_cv_versions"
down_revision = "0003_add_skills_and_settings"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "cv_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("job_description", sa.Text, nullable=False),
        sa.Column("data", postgresql.JSONB, nullable=False),
        sa.Column("pdf_url", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

def downgrade():
    op.drop_table("cv_versions")
