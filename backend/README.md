# Portfolio backend

Phase 1 contains the PostgreSQL schema and Alembic migration foundation. API routes are deferred to Phase 2.

The schema keeps timeline-like content in `entries`; profile/contact data and other collections use separate tables because they do not share the entry lifecycle or rendering model.

Install shared dependencies from the repository root with `pip install -r requirements.txt`.
