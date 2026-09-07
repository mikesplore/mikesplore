"""Add explicit graph relationships between content nodes."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_relationships"
down_revision = "0009_content_blocks"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("subject_type", sa.Text, nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("predicate", sa.Text, nullable=False),
        sa.Column("object_type", sa.Text, nullable=False),
        sa.Column("object_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.Text),
    )
    op.create_index("ix_relationships_subject", "relationships", ["subject_type", "subject_id"])
    op.create_index("ix_relationships_object", "relationships", ["object_type", "object_id"])


def downgrade():
    op.drop_index("ix_relationships_object", table_name="relationships")
    op.drop_index("ix_relationships_subject", table_name="relationships")
    op.drop_table("relationships")
