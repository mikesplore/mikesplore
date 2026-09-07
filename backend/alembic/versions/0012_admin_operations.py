"""Add durable admin operations and audit records."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_admin_operations"
down_revision = "0011_cleanup_legacy"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "admin_operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("telegram_user_id", sa.BigInteger, nullable=False),
        sa.Column("instruction", sa.Text, nullable=False),
        sa.Column("operation", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("error_detail", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_admin_operations_user_status", "admin_operations", ["telegram_user_id", "status"])
    op.create_table(
        "admin_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admin_operations.id", ondelete="SET NULL")),
        sa.Column("telegram_user_id", sa.BigInteger, nullable=False),
        sa.Column("resource", sa.String(64), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("record_id", sa.String(160)),
        sa.Column("before_value", postgresql.JSONB),
        sa.Column("after_value", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table("admin_audit_log")
    op.drop_index("ix_admin_operations_user_status", table_name="admin_operations")
    op.drop_table("admin_operations")
