# Mikesplore

> **The digital showcase and interactive AI assistant for Michael Odhiambo.**  
> Full-stack systems, production projects, technical writing, and live interactive AI workflows.

<p align="center">
  <a href="https://mikesplore.me"><strong>Visit Website (mikesplore.me)</strong></a> •
  <a href="https://mikesplore.me"><strong>Open the voice representative</strong></a>
</p>

<p align="center">
  <img src="https://readme-stats-github.pages.dev/api?username=mikesplore&theme=dark" alt="GitHub Stats" />
</p>

---

## What's Inside?

The main portfolio is available at **[mikesplore.me](https://mikesplore.me)**. This branch contains
the standalone AssemblyAI voice representative and is deployed as separate frontend, voice-gateway,
and main-backend services:

* **Voice-first interface:** Milo is the complete frontend entry point; there is no dashboard or secondary voice route in this branch.
* **Verified public browsing:** Ask about projects, profile information, links, certificates, CV resources, skills, and education.
* **Owner mode:** PIN-gated actions can update the profile, CV, projects, certificates, links, skills, and education, with confirmation before writes.
* **Live speech:** AssemblyAI handles realtime speech recognition and agent responses; the browser plays the returned PCM audio.

---

## Tech Stack Overview

Built with **React**, **FastAPI**, **PostgreSQL**, **AssemblyAI Voice Agent API**, and **Cloudflare R2**.

## Architecture

This branch separates the voice gateway from the main portfolio backend:

```text
Voice frontend
  ├── main backend REST API → PostgreSQL and Cloudflare R2
  └── voice gateway → AssemblyAI Voice Agent API
```

The gateway has no database connection. It forwards verified portfolio tools to the main backend,
while the main backend remains responsible for persistence, media, and owner-session authorization.
Public questions are read-only. Profile, CV, project, certificate, link, skill, and education
changes require the owner PIN and an explicit browser confirmation.

---

## Local Setup

```bash
# Set up dependencies from the repository root
pip install -r requirements.txt

# Main portfolio backend (database/API service)
alembic -c backend/alembic.ini upgrade head
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# In a second terminal: AssemblyAI voice gateway (no database connection)
uvicorn voice_gateway.app.gateway:app --host 0.0.0.0 --port 8001 --reload

# In a third terminal: frontend
cd frontend
npm install
npm run dev
```

The frontend opens Milo directly at `/`.

### Deployment

Deploy two Render web services from this repository:

Main portfolio backend:

```text
Pre-deploy: alembic -c backend/alembic.ini upgrade head
Start:      uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

AssemblyAI voice gateway:

```text
Pre-deploy: none
Start:      uvicorn voice_gateway.app.gateway:app --host 0.0.0.0 --port $PORT
```

Set `VITE_API_BASE_URL` to the main portfolio backend URL and `VITE_VOICE_API_BASE_URL` to the
standalone voice gateway URL when building the frontend. The voice WebSocket uses `wss://`
automatically on HTTPS deployments. Keep `OWNER_PIN`, service keys, storage credentials, and
`ASSEMBLYAI_API_KEY` in the host's secret environment configuration.
