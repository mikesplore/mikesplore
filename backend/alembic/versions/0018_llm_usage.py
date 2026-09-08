"""Track LLM token usage without storing prompts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0018_llm_usage"
down_revision = "0017_repository_visibility"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "llm_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("workflow", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("request_id", sa.String(length=255)),
        sa.Column("input_tokens", sa.BigInteger()),
        sa.Column("cached_input_tokens", sa.BigInteger()),
        sa.Column("output_tokens", sa.BigInteger()),
        sa.Column("total_tokens", sa.BigInteger()),
        sa.Column("input_characters", sa.BigInteger()),
        sa.Column("tool_payload_characters", sa.BigInteger()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("error_code", sa.String(length=128)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_llm_usage_created_at", "llm_usage", ["created_at"])
    op.create_index("ix_llm_usage_workflow", "llm_usage", ["workflow"])


def downgrade():
    op.drop_index("ix_llm_usage_workflow", table_name="llm_usage")
    op.drop_index("ix_llm_usage_created_at", table_name="llm_usage")
    op.drop_table("llm_usage")
