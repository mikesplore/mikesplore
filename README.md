# Mikesplore

Mikesplore is a production-style personal portfolio platform and Telegram assistant. The website
serves curated projects, articles, hackathons, events, skills, certificates, and career information
from a PostgreSQL-backed FastAPI API. The React frontend consumes the public API at runtime, while
the Telegram bot provides grounded portfolio questions, CV delivery, CV tailoring, and protected
content management workflows.

The platform is built with React, Vite, FastAPI, PostgreSQL, Alembic, Telegram, Groq, and Cloudflare
R2. It uses service-key-protected administrative endpoints, Telegram administrator authorization,
LLM tool calling for verified answers, and deterministic PDF rendering for tailored CVs.

## Links

- Website: [mikesplore.me](https://mikesplore.me)
- Telegram bot: [@mikesplorebot](https://t.me/mikesplorebot)

## GitHub Stats

<p>
  <img src="https://img.shields.io/github/followers/mikesplore?label=Followers&style=for-the-badge" alt="GitHub followers">
  <img src="https://img.shields.io/github/stars/mikesplore?affiliations=OWNER%2CCOLLABORATOR&label=Total%20stars&style=for-the-badge" alt="GitHub stars">
  <img src="https://img.shields.io/github/repos/mikesplore?label=Public%20repositories&style=for-the-badge" alt="Public repositories">
</p>
<p>
  <a href="https://github.com/mikesplore?tab=repositories">View all repositories and activity on GitHub</a>
</p>

## Local Development

Install the shared Python dependencies and configure the root `.env` using `.env.example`.

```bash
pip install -r requirements.txt
alembic -c backend/alembic.ini upgrade head
uvicorn backend.app.main:app --reload
```

The frontend is developed separately from `frontend/` with `npm install` and `npm run dev`.
