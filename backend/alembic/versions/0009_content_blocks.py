"""Add normalized project content blocks."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_content_blocks"
down_revision = "0008_merge_projects_repositories"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)

def upgrade():
    specs = {
        "topology_steps": [("order_index", sa.Integer, False), ("role_label", sa.Text, True), ("icon", sa.Text, True), ("title", sa.Text, True), ("description", sa.Text, True), ("footnote_label", sa.Text, True), ("footnote_value", sa.Text, True)],
        "metrics": [("label", sa.Text, True), ("value", sa.Text, True), ("unit", sa.Text, True), ("group_tag", sa.Text, True), ("is_highlighted", sa.Boolean, False), ("order_index", sa.Integer, False)],
        "architecture_decisions": [("icon", sa.Text, True), ("title", sa.Text, True), ("body", sa.Text, True), ("order_index", sa.Integer, False)],
        "highlights": [("icon", sa.Text, True), ("title", sa.Text, True), ("description", sa.Text, True), ("order_index", sa.Integer, False)],
        "quotes": [("quote_text", sa.Text, True), ("attribution_name", sa.Text, True), ("attribution_role", sa.Text, True), ("context_label", sa.Text, True)],
        "code_snippets": [("label", sa.Text, True), ("language", sa.Text, True), ("code", sa.Text, True), ("is_copyable", sa.Boolean, False), ("order_index", sa.Integer, False)],
        "documents": [("title", sa.Text, True), ("url", sa.Text, True), ("icon", sa.Text, True), ("link_style", sa.Text, True), ("order_index", sa.Integer, False)],
        "badges": [("label", sa.Text, True), ("style", sa.Text, True), ("order_index", sa.Integer, False)],
    }
    for table, fields in specs.items():
        columns = [sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("entry_id", UUID, sa.ForeignKey("entries.id", ondelete="CASCADE"), nullable=False)]
        for name, typ, nullable in fields:
            default = sa.false() if name in {"is_highlighted", "is_copyable"} else (0 if name == "order_index" else None)
            columns.append(sa.Column(name, typ, nullable=nullable, server_default=sa.text(str(default).lower()) if default is not None else None))
        op.create_table(table, *columns)

def downgrade():
    for table in ("badges", "documents", "code_snippets", "quotes", "highlights", "architecture_decisions", "metrics", "topology_steps"):
        op.drop_table(table)
