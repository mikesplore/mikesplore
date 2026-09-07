"""Extend entries and normalize technology names."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_normalize_technologies"
down_revision = "0006_projects_and_repositories"
branch_labels = None
depends_on = None


def upgrade():
    for name in ("icon_label", "icon_url", "status", "version", "license", "category", "author_role", "origin"):
        op.add_column("entries", sa.Column(name, sa.Text))
    op.add_column("entries", sa.Column("started_at", sa.Date))
    op.add_column("entries", sa.Column("ended_at", sa.Date))
    op.add_column("entries", sa.Column("template", sa.Text, nullable=False, server_default="standard"))
    op.create_table(
        "technologies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("category", sa.Text),
    )
    op.create_table(
        "entry_technologies",
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("technology_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("technologies.id", ondelete="CASCADE"), nullable=False),
        sa.PrimaryKeyConstraint("entry_id", "technology_id"),
    )
    op.execute("""INSERT INTO technologies (name)
        SELECT DISTINCT trim(tech) FROM entries CROSS JOIN LATERAL unnest(entries.tech_stack) AS tech
        WHERE trim(tech) <> '' ON CONFLICT (name) DO NOTHING""")
    op.execute("""INSERT INTO entry_technologies (entry_id, technology_id)
        SELECT e.id, t.id FROM entries e CROSS JOIN LATERAL unnest(e.tech_stack) AS tech
        JOIN technologies t ON t.name = trim(tech) ON CONFLICT DO NOTHING""")


def downgrade():
    op.drop_table("entry_technologies")
    op.drop_table("technologies")
    for name in ("template", "ended_at", "started_at", "origin", "author_role", "category", "license", "version", "status", "icon_url", "icon_label"):
        op.drop_column("entries", name)
