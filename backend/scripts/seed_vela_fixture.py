"""Seed a small, repeatable Vela project graph for API/site verification.

Run from the repository root after migrations:
    python -m backend.scripts.seed_vela_fixture
"""
from datetime import date

from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import (
    ArchitectureDecision,
    Entry,
    EntryTechnology,
    Highlight,
    Metric,
    Relationship,
    Repository,
    Technology,
    TopologyStep,
)


PROJECTS = {
    "vela": {
        "title": "Vela",
        "blurb": "Cross-platform remote device orchestration via natural language.",
        "status": "active",
        "category": "android",
        "origin": "portfolio",
        "started_at": date(2024, 1, 1),
        "tags": ["Android", "AI", "Remote Control"],
    },
    "vela-mcp": {
        "title": "Vela MCP Server",
        "blurb": "MCP server exposing Vela RemotePC endpoints as tools for AI clients.",
        "status": "active",
        "category": "tooling",
        "origin": "portfolio",
        "tags": ["AI", "MCP", "Tooling"],
    },
    "velavps": {
        "title": "Vela VPS",
        "blurb": "Vela backend infrastructure for remotely orchestrating connected devices.",
        "status": "active",
        "category": "infrastructure",
        "origin": "portfolio",
        "tags": ["Infrastructure", "FastAPI", "Remote Control"],
    },
    "vela-android": {
        "title": "Vela Android",
        "blurb": "Native Android client for controlling remote devices through Vela.",
        "status": "active",
        "category": "android",
        "origin": "portfolio",
        "tags": ["Android", "Kotlin", "Remote Control"],
    },
}

REPOSITORIES = {
    "vela": "https://github.com/mikesplore/vela",
    "vela-mcp": "https://github.com/mikesplore/vela-mcp",
    "velavps": "https://github.com/mikesplore/velavps",
    "vela-android": "https://github.com/mikesplore/vela-android",
}

TECHNOLOGIES = {
    "vela": ["Kotlin", "Python", "FastAPI", "LLM Function Calling"],
    "vela-mcp": ["Python", "FastAPI", "MCP", "HTTP", "STDIO"],
    "velavps": ["Python", "FastAPI", "PostgreSQL"],
    "vela-android": ["Kotlin", "Android"],
}


def get_or_create_entry(db, slug: str, values: dict) -> Entry:
    entry = db.scalar(select(Entry).where(Entry.slug == slug))
    if not entry:
        entry = Entry(slug=slug, content_type="project")
        db.add(entry)
    for key, value in values.items():
        setattr(entry, key, value)
    entry.is_visible = True
    entry.is_featured = slug == "vela"
    entry.custom_order = 0 if slug == "vela" else 10
    return entry


def run():
    with SessionLocal() as db:
        entries = {slug: get_or_create_entry(db, slug, values) for slug, values in PROJECTS.items()}
        db.flush()

        for slug, names in TECHNOLOGIES.items():
            entry = entries[slug]
            for name in names:
                technology = db.scalar(select(Technology).where(Technology.name == name))
                if not technology:
                    technology = Technology(name=name, category="technology")
                    db.add(technology)
                    db.flush()
                if not db.scalar(select(EntryTechnology).where(EntryTechnology.entry_id == entry.id, EntryTechnology.technology_id == technology.id)):
                    db.add(EntryTechnology(entry_id=entry.id, technology_id=technology.id))

        for slug, url in REPOSITORIES.items():
            entry = entries[slug]
            repository = db.scalar(select(Repository).where(Repository.url == url))
            if not repository:
                repository = Repository(entry_id=entry.id, name=entry.title, url=url, is_primary=True)
                db.add(repository)
            else:
                repository.entry_id = entry.id
                repository.is_primary = True

        vela = entries["vela"]
        if not db.scalar(select(TopologyStep).where(TopologyStep.entry_id == vela.id)):
            db.add_all([
                TopologyStep(entry_id=vela.id, order_index=0, role_label="Client", title="Natural language intent", description="The user describes a device action in plain language."),
                TopologyStep(entry_id=vela.id, order_index=1, role_label="Backend", title="Intent routing", description="The backend translates the intent into a device operation."),
                TopologyStep(entry_id=vela.id, order_index=2, role_label="Device", title="Remote execution", description="The connected device executes the approved action."),
            ])
        if not db.scalar(select(Metric).where(Metric.entry_id == vela.id)):
            db.add_all([
                Metric(entry_id=vela.id, label="Primary client", value="Android", group_tag="platform", is_highlighted=True),
                Metric(entry_id=vela.id, label="Control interface", value="Natural language", group_tag="experience", is_highlighted=True),
            ])
        if not db.scalar(select(ArchitectureDecision).where(ArchitectureDecision.entry_id == vela.id)):
            db.add(ArchitectureDecision(entry_id=vela.id, order_index=0, title="Separate client and orchestration layers", body="Keep device interaction, intent processing, and remote execution independently extensible."))
        if not db.scalar(select(Highlight).where(Highlight.entry_id == vela.id)):
            db.add(Highlight(entry_id=vela.id, order_index=0, title="One Vela graph", description="The Android client, VPS backend, and MCP server are represented as related project nodes."))

        for child_slug in ("vela-mcp", "velavps", "vela-android"):
            child = entries[child_slug]
            existing = db.scalar(select(Relationship).where(Relationship.subject_type == "entry", Relationship.subject_id == child.id, Relationship.predicate == "related_to", Relationship.object_type == "entry", Relationship.object_id == vela.id))
            if not existing:
                db.add(Relationship(subject_type="entry", subject_id=child.id, predicate="related_to", object_type="entry", object_id=vela.id, note="Part of the Vela project family"))

        db.commit()
        print("Seeded Vela project graph: " + ", ".join(PROJECTS))


if __name__ == "__main__":
    run()
