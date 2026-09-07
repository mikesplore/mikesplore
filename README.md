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
  <img src="https://github-readme-stats.vercel.app/api?username=mikesplore&show_icons=true&hide_border=true&rank_icon=github" alt="Mikesplore GitHub stats" height="165">
  <img src="https://github-readme-stats.vercel.app/api/top-langs/?username=mikesplore&layout=compact&hide_border=true" alt="Top languages" height="165">
</p>

## Local Development

Install the shared Python dependencies and configure the root `.env` using `.env.example`.

```bash
pip install -r requirements.txt
alembic -c backend/alembic.ini upgrade head
uvicorn backend.app.main:app --reload
```

The frontend is developed separately from `frontend/` with `npm install` and `npm run dev`.
